from bson import ObjectId

class MongoEntity:
    @staticmethod
    def serialize_id(document: dict) -> dict:
        if document and "_id" in document:
            document["id"] = str(document["_id"])
            del document["_id"]
        return document

    @staticmethod
    def serialize_list(documents: list) -> list:
        return [MongoEntity.serialize_id(doc) for doc in documents]