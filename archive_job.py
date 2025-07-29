from azure.cosmos import CosmosClient
from azure.storage.blob import BlobClient
import gzip, json
import datetime

THRESHOLD = datetime.utcnow() - datetime.timedelta(days=90)

client = CosmosClient(...)
container = client.get_container_client('billing')
blob_container = BlobServiceClient(...).get_container_client('archive')

for item in container.query_items(
    f"SELECT * FROM c WHERE c.createdAt < '{THRESHOLD.isoformat()}'", enable_cross_partition_query=True):
    id = item['id']
    data = json.dumps(item).encode('utf-8')
    blob_name = f"{item['partitionKey']}/{id}.json.gz"
    blob_client = blob_container.get_blob_client(blob_name)
    blob_client.upload_blob(gzip.compress(data), overwrite=True)
    # insert stub
    stub = {'id': id, 'partitionKey': item['partitionKey'],
            '_isArchived': True, 'blobPath': blob_name, 'createdAt': datetime.utcnow().isoformat()}
    container.upsert_item(stub)
    container.delete_item(id, partition_key=item['partitionKey'])
