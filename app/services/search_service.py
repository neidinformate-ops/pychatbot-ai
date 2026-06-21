import requests
import numpy as np

from app.config import (
    SUPABASE_URL,
    HEADERS
)

from app.services.embedding_service import (
    create_embedding
)


# =====================================
# COSINE SIMILARITY
# =====================================

def cosine_similarity(a, b):

    a = np.array(a)

    b = np.array(b)


    denominator = (

        np.linalg.norm(a)

        *

        np.linalg.norm(b)

    )


    if denominator == 0:

        return 0


    return (

        np.dot(a, b)

        /

        denominator

    )


# =====================================
# SEMANTIC SEARCH
# =====================================

def semantic_search(

    assistant_id: str,

    query: str,

    limit: int = 5

):

    try:


        query_embedding = (

            create_embedding(

                query

            )

        )


        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

            headers=HEADERS,

            params={

                "assistant_id":

                f"eq.{assistant_id}"

            }

        )


        knowledge = response.json()


        results = []


        for item in knowledge:


            embedding = item.get(

                "embedding"

            )


            if not embedding:

                continue


            similarity = (

                cosine_similarity(

                    query_embedding,

                    embedding

                )

            )


            results.append({

                "content":

                item["content"],


                "score":

                similarity,


                "source":

                item.get(

                    "source",

                    ""

                )

            })


        results.sort(

            key=lambda x:

            x["score"],

            reverse=True

        )


        return results[:limit]


    except Exception as e:


        print(

            "SEMANTIC SEARCH ERROR:",

            e

        )


        return []