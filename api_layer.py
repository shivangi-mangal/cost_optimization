item = container.read_item(id, partition_key=pk)
if item.get('_isArchived'):
    blob = blob_container.get_blob_client(item['blobPath']).download_blob().readall()
    data = json.loads(gzip.decompress(blob))
    return data
else:
    return item
