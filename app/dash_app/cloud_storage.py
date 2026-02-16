import os
import uuid
import s3fs
import gcsfs
import re
import pyarrow as pa
import pyarrow.dataset as ds
import logging
import pandas as pd
from typing import List, Any, Literal
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class CloudStorage:
    """
    S3-compatible and GCS-compatible storage client for storing and loading data.
    """
    def __init__(self, protocol: str = None, endpoint: str = None):
        self.protocol = (protocol or 's3').lower()
        self.endpoint = endpoint or 'http://localhost:9000'
        self.bucket = os.getenv("ETL_BUCKET", "etl-bucket")
        
        if self.protocol == 's3':
            self.fs = s3fs.S3FileSystem(
                client_kwargs={'endpoint_url': self.endpoint},
                key=os.getenv("STORAGE_USER", "admin"),
                secret=os.getenv("STORAGE_PASSWORD", ""), 
            )
        elif self.protocol in ('gcs', 'gs'):
            # GCSFS will use Google Application Default Credentials (ADC) automatically
            # Ensure GOOGLE_APPLICATION_CREDENTIALS env var is set or gcloud auth is configured
            project_id = os.getenv("GCS_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
            self.fs = gcsfs.GCSFileSystem(project=project_id)
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol!r}")

    def slugify(self, text: str) -> str:
        """Converts 'Coffee Cup' to 'coffee_cup'."""
        text = text.lower()
        text = re.sub(r'[\s]+', '_', text)
        text = re.sub(r'[^a-z0-9_]', '', text)
        return text
    
    def store_data_parquet(self, dataframe: pd.DataFrame, path: str = '', partition_cols: List[str] = None, file_name: str = 'data.parquet'):
        path = f'{path.strip("/")}/' if path else ''
        target = f'{self.bucket}/{path}{file_name}'

        if partition_cols:
            dataframe.to_parquet(
                target,
                engine='pyarrow',
                partition_cols=partition_cols,
                filesystem=self.fs,
                index=False,
            )
        else:
            dataframe.to_parquet(
                target,
                engine='pyarrow',
                filesystem=self.fs,
                index=False,
            )
        logger.info(f'Stored DataFrame to {target}')

    def load_parquet(self, path: str, file_name: str = None) -> pd.DataFrame:
        if not path:
            raise ValueError("`path` must be provided and non-empty")

        key = path.lstrip('/')
        if file_name:
            key = f"{key.rstrip('/')}/{file_name.lstrip('/')}"
        uri = f"{self.bucket}/{key}"

        logger.debug(f'Loading parquet from {self.protocol}: {uri}')
        try:
            df = pd.read_parquet(
                uri,
                engine="pyarrow",
                filesystem=self.fs,
            )
            logger.info(f'Loaded DataFrame from {uri} with shape {df.shape}')
            return df
        except Exception as e:
            logger.error(f'Error loading parquet from {self.protocol}: {e}')
            return pd.DataFrame()

    def append_to_dataset_parquet(self, dataframe: pd.DataFrame, path: str, file_name: str):
        try:
            existing_df = self.load_parquet(path=path, file_name=file_name)
            if not existing_df.empty:
                dataframe = pd.concat([existing_df, dataframe], ignore_index=True)
        except Exception:
            pass
        
        self.store_data_parquet(dataframe=dataframe, path=path, file_name=file_name)

    def _dataset_base_dir(self, path: str) -> str:
        path = path.strip('/')
        return f'{self.bucket}/{path}' if path else f'{self.bucket}'

    @staticmethod
    def _promote_nulls_to_string(schema: pa.Schema, hints: dict[str, pa.DataType] | None = None) -> pa.Schema:
        hints = hints or {}
        fields: list[pa.Field] = []
        for f in schema:
            if f.name in hints:
                fields.append(pa.field(f.name, hints[f.name]))
            elif pa.types.is_null(f.type):
                fields.append(pa.field(f.name, pa.string()))
            else:
                fields.append(f)
        return pa.schema(fields)

    @staticmethod
    def _normalize_for_write(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        for c in df.columns:
            if df[c].dtype == object or pd.api.types.is_string_dtype(df[c]):
                df[c] = df[c].astype('string')
        return df

    @staticmethod
    def _schema_from_df(df: pd.DataFrame, schema_hints: dict[str, pa.DataType] | None = None) -> pa.Schema:
        table = pa.Table.from_pandas(df, preserve_index=False)
        schema = table.schema
        if not schema_hints:
            return schema
        fields: list[pa.Field] = []
        for f in schema:
            fields.append(pa.field(f.name, schema_hints[f.name]) if f.name in schema_hints else f)
        return pa.schema(fields)

    def load_dataset_parquet(self, path: str, columns: list[str] | None = None, schema_hints: dict[str, pa.DataType] | None = None) -> pd.DataFrame:
        if not path:
            raise ValueError('`path` must be provided and non-empty')

        base_dir = self._dataset_base_dir(path)

        try:
            ds0 = ds.dataset(
                base_dir,
                filesystem=self.fs,
                format='parquet',
                partitioning='hive',
                exclude_invalid_files=True,
            )
            promoted_schema = self._promote_nulls_to_string(ds0.schema, hints=schema_hints)
            dataset = ds.dataset(
                base_dir,
                filesystem=self.fs,
                format='parquet',
                partitioning='hive',
                exclude_invalid_files=True,
                schema=promoted_schema,
            )
            scanner = ds.Scanner.from_dataset(dataset=dataset, columns=columns, use_threads=True)
            return scanner.to_table().to_pandas()
        except Exception as e:
            logger.error(f'Error loading dataset from {base_dir}: {e}')
            return pd.DataFrame()

    def store_dataset_parquet(
        self,
        dataframe: pd.DataFrame,
        path: str,
        partition_cols: list[str] | None = None,
        schema_hints: dict[str, pa.DataType] | None = None,
        mode: Literal['append', 'overwrite_or_ignore', 'delete_matching'] = 'append',
        logger: logging.Logger | None = None,
    ) -> None:
        if dataframe is None or dataframe.empty:
            if logger:
                logger.warning(f"Skipping storage for {path}: DataFrame is empty.")
            return

        df = self._normalize_for_write(dataframe.copy())
        base_dir = self._dataset_base_dir(path)
        schema = self._schema_from_df(df, schema_hints=schema_hints)
        table = pa.Table.from_pandas(df, preserve_index=False, schema=schema)

        behavior_map = {
            'append': 'overwrite_or_ignore',
            'overwrite_or_ignore': 'overwrite_or_ignore',
            'delete_matching': 'delete_matching',
        }
        write_kwargs = {}
        if behavior_map.get(mode):
            write_kwargs['existing_data_behavior'] = behavior_map[mode]

        write_kwargs['basename_template'] = f'part-{{i}}-{uuid.uuid4().hex}.parquet'

        partitioning = None
        if partition_cols:
            part_schema = pa.schema([table.schema.field(c) for c in partition_cols])
            partitioning = ds.partitioning(part_schema, flavor='hive')

        ds.write_dataset(
            data=table,
            base_dir=base_dir,
            filesystem=self.fs,
            format='parquet',
            partitioning=partitioning,
            **write_kwargs
        )

    def append_dataset_parquet(
        self,
        dataframe: pd.DataFrame,
        path: str,
        partition_cols: list[str] | None = None,
        schema_hints: dict[str, pa.DataType] | None = None,
        replace_partitions: bool = False,
        logger: logging.Logger | None = None,
    ):
        mode = 'delete_matching' if replace_partitions and partition_cols else 'append'
        self.store_dataset_parquet(dataframe=dataframe, path=path, partition_cols=partition_cols, schema_hints=schema_hints, mode=mode, logger=logger)