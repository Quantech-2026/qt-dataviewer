import gzip


def get_snapshot(ds):
    if ds is None:
        return None
    if 'snapshot' in ds.attrs:
        return ds.attrs['snapshot']
    elif 'snapshot-gzip' in ds.attrs:
        return gzip.decompress(ds.attrs['snapshot-gzip']).decode("utf-8")
    return None
