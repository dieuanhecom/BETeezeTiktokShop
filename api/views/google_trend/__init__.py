import json
import logging
import os
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

from api import setup_logging
from api.views import APIView, HttpResponse, JsonResponse

load_dotenv(override=True)

logger = logging.getLogger("api.views.google_trend")
setup_logging(logger, level=logging.WARNING)


# Decorator serve request
def serve_connection(func):
    def wrapper(*args, **kwargs):
        conn = psycopg2.connect(
            host=os.getenv("DB_GGTREND_HOST"),
            port=os.getenv("DB_GGTREND_PORT"),
            user=os.getenv("DB_GGTREND_USER"),
            password=os.getenv("DB_GGTREND_PASSWORD"),
            database=os.getenv("DB_GGTREND_NAME"),
        )
        try:
            return func(conn, *args, **kwargs)
        except psycopg2.Error:
            logger.error("Postgres error", exc_info=True)
            return JsonResponse({"error": "Internal server error"}, status=500)
        except Exception:
            logger.error("Unknown error", exc_info=True)
            return JsonResponse({"error": "Internal server error"}, status=500)
        finally:
            conn.close()

    return wrapper


@serve_connection
def _query_options(conn) -> tuple:
    with conn.cursor() as cur:
        # Get all keywords
        cur.execute("SELECT DISTINCT keyword FROM ggtrend.data")
        all_keywords: list = [keyword[0] for keyword in cur.fetchall()]

        # Get all time frames
        cur.execute("SELECT DISTINCT name FROM ggtrend.timeframe")
        all_time_frames: list = [time_frame[0] for time_frame in cur.fetchall()]

        logger.info(f"Key words: {', '.join(all_keywords)}\nTime frames: {', '.join(all_time_frames)}")

        return all_keywords, all_time_frames


@serve_connection
def _query_google_trend(conn, time_frame, keyword, max_results=10) -> list:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
                content,
                time_crawl
            from ggtrend.data as d
            join ggtrend.timeframe as tf
                on d.timeframe_id = tf.timeframe_id
            where 1 = 1
                and tf.name = %s
                and keyword = %s
            order by time_crawl desc
            limit %s;
            """,
            (time_frame, keyword, max_results),
        )
        data = cur.fetchall()
        data = [{"content": row[0], "time_crawl": datetime.strftime(row[1], "%Y-%m-%d %H:%M:%S")} for row in data]

        return json.dumps(data, ensure_ascii=False)


class GoogleTrendOptions(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(f"User {request.user} requested Google Trend options")
        try:
            all_keywords, all_time_frames = _query_options()
            return JsonResponse({"keywords": all_keywords, "time_frames": all_time_frames}, status=200)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return JsonResponse({"error": f"Internal server error {str(e)}"}, status=500)


class QueryGoogleTrend(APIView):
    def get(self, request):
        try:
            time_frame = request.GET.get("time_frame", "")
            keyword = request.GET.get("keyword", "")

            max_results_str = request.GET.get("max_results", "10")

            if max_results_str.isdigit():
                max_results = int(max_results_str)
            else:
                max_results = 10

            result = _query_google_trend(time_frame, keyword, max_results)

            return HttpResponse(result, status=200)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return JsonResponse({"error": f"Internal server error {str(e)}"}, status=500, safe=False)
