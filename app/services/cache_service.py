import redis
import json
import os


redis_client = redis.Redis(

    host=os.getenv("REDIS_HOST"),

    port=int(

        os.getenv(

            "REDIS_PORT",

            6379

        )

    ),

    password=os.getenv(

        "REDIS_PASSWORD"

    ),

    decode_responses=True

)

def get_cache(

    key

):

    try:

        value = redis_client.get(

            key

        )


        if not value:

            return None


        return json.loads(

            value

        )


    except:

        return None

    def set_cache(

            key,

            value,

            ttl=3600

    ):

        redis_client.setex(

            key,

            ttl,

            json.dumps(

                value

            )

        )