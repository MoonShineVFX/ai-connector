from elasticsearch import Elasticsearch, JsonSerializer
from defines import Settings
from typing import Any
from PIL.Image import Image


class JsonPILSerializer(JsonSerializer):
    def default(self, data: Any) -> Any:
        if isinstance(data, Image):
            return f"PIL.Image ({data.width}x{data.height} / {data.format})"
        return super().default(data)


elastic_client = Elasticsearch(
    cloud_id=Settings.ELASTIC_CLOUD_ID,
    api_key=Settings.ELASTIC_API_KEY,
    serializers={"application/json": JsonPILSerializer()},
)
