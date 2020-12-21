import os

import kopf
from schema_registry.client import AsyncSchemaRegistryClient, schema

# Configuration
schema_registry_url = os.getenv("SCHEMA_REGISTY_URL", default="http://localhost:8081")
apply_timeout = int(os.getenv("APPLY_TIMEOUT", default=10))

REGISTRY = AsyncSchemaRegistryClient(url=schema_registry_url)


async def add_key_schema(topic: str, s: dict) -> int:
    subject = f"{topic}-key"
    return await REGISTRY.register(subject, schema.AvroSchema(s), timeout=apply_timeout)


async def add_value_schema(topic: str, s: dict) -> int:
    subject = f"{topic}-value"
    return await REGISTRY.register(subject, schema.AvroSchema(s), timeout=apply_timeout)


@kopf.on.create("dlmiddlecote.io", "v1", "kafkatopicschemas")
@kopf.on.update("dlmiddlecote.io", "v1", "kafkatopicschemas")
async def add_kafka_topic_schema(spec, patch, **kwargs):
    def add_status(status: dict):
        patch.setdefault("status", {}).update(status)

    def add_result(msg: str):
        add_status({"result": msg})

    topic = spec.get("topic")
    if not topic:
        add_result("Topic not specified")
        raise kopf.PermanentError("Type not specified")

    key_schema = spec.get("keySchema")
    if key_schema:
        try:
            keyID = await add_key_schema(topic, key_schema)
        except Exception as e:
            add_result(f"Cannot add key schema: {e}")
            raise kopf.PermanentError(f"Cannot add key schema: {e}")
        else:
            add_status({"keySchemaID": keyID})

    value_schema = spec.get("valueSchema")
    if value_schema:
        try:
            valueID = await add_value_schema(topic, value_schema)
        except Exception as e:
            add_result(f"Cannot add value schema: {e}")
            raise kopf.PermanentError(f"Cannot add key schema: {e}")
        else:
            add_status({"valueSchemaID": valueID})

    add_result("OK")


@kopf.on.delete("dlmiddlecote.io", "v1", "kafkatopicschemas")
async def delete_kafka_topic_schema(spec, **kwargs):
    topic = spec.get("topic")
    if not topic:
        return

    try:
        await REGISTRY.delete_subject(f"{topic}-key", timeout=apply_timeout)
    except Exception:
        pass

    try:
        await REGISTRY.delete_subject(f"{topic}-value", timeout=apply_timeout)
    except Exception:
        pass
