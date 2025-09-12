import concurrent

from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden
from rest_framework.views import APIView
from datetime import datetime, timedelta
import pytz

from api.models import UserShop, Shop
from api.utils.constants.statement import payment_status
from api.utils.pagination import get_pagination
from api.utils.tiktok_base_api.finance import (
    get_statements_all,
    get_statement_transactions,
)
from api.views.tiktok import get_all_order, get_shop_list
from concurrent.futures import ThreadPoolExecutor


class StatisticsFinanceApi(APIView):
    def fetch_statements(
        self, shop: Shop, filters: dict, user_ids: list, payment_status: tuple
    ):
        user_shop = UserShop.objects.filter(shop_id=shop.id).first()
        user = None
        if user_shop:
            user = User.objects.filter(id=user_shop.user_id).first()
        if user.id not in user_ids:
            return []
        query = {
            "shop_cipher": shop.shop_cipher,
        }
        query.update(filters)
        return get_statements_all(shop, user, query, payment_status)

    def fetch_statements_with_order(self, statement):
        statement_id = statement.get("id")
        shop = statement.get("shop")
        statement_with_order = get_statement_transactions(statement_id, shop, {})
        return statement_with_order

    def get_statements(self, filters, shops, user_ids):
        now = datetime.now(pytz.utc)
        default_time_ge = int((now - timedelta(days=1)).timestamp())
        default_time_lt = int(now.timestamp())

        payment_status_value = filters.get("payment_status", {}).get("$in", "")
        payment_status_tuple = (
            tuple(set(payment_status_value.split(",")))
            if payment_status_value
            else (payment_status["PAID"],)
        )

        filters = {
            "statement_time_ge": int(
                filters.get("statement_time", {}).get("$gte", default_time_ge)
            ),
            "statement_time_lt": int(
                filters.get("statement_time", {}).get("$lt", default_time_lt)
            ),
            "sort_field": "statement_time",
            "page_size": 100,
        }

        statements = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_shop = {
                executor.submit(
                    self.fetch_statements,
                    shop,
                    filters,
                    user_ids,
                    payment_status_tuple,
                ): shop
                for shop in shops
            }
            for future in concurrent.futures.as_completed(future_to_shop):
                statements.extend(future.result())
        return statements

    def get_statements_with_order(self, filters, shops, user_ids):
        statements = self.get_statements(filters, shops, user_ids)
        statements_with_order = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_shop = {
                executor.submit(
                    self.fetch_statements_with_order,
                    statement,
                ): statement
                for statement in statements
            }
            for future in concurrent.futures.as_completed(future_to_shop):
                statements_with_order.append(future.result())
        return statements_with_order

    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Unauthorized", content_type="text/plain")
            pagination, filters, sorts = get_pagination(
                request,
                [
                    "statement_time",
                    "order_status",
                    "shop_id",
                    "user_id",
                    "payment_status",
                ],
            )
            user = request.user
            shops, user_ids = get_shop_list(user, filters)
            statements = self.get_statements(filters, shops, user_ids)

            stats = {}
            for statement in statements:
                date_str = datetime.fromtimestamp(
                    statement["statement_time"], pytz.utc
                ).strftime("%Y-%m-%d")
                if date_str not in stats:
                    stats[date_str] = {
                        "statements": {
                            "status": {},
                            "shops": [],
                        },
                    }
                payment_status = statement["payment_status"]
                revenue_amount = float(statement["revenue_amount"])
                settlement_amount = float(statement["settlement_amount"])
                fee_amount = float(statement["fee_amount"])
                adjustment_amount = float(statement["adjustment_amount"])
                stats[date_str]["statements"]["status"].setdefault(
                    "TOTAL",
                    {
                        "revenue_amount": 0,
                        "settlement_amount": 0,
                        "fee_amount": 0,
                        "adjustment_amount": 0,
                    },
                )
                stats[date_str]["statements"]["status"].setdefault(
                    payment_status,
                    {
                        "revenue_amount": 0,
                        "settlement_amount": 0,
                        "fee_amount": 0,
                        "adjustment_amount": 0,
                    },
                )
                stats[date_str]["statements"]["status"]["TOTAL"][
                    "revenue_amount"
                ] = round(
                    stats[date_str]["statements"]["status"]["TOTAL"]["revenue_amount"]
                    + revenue_amount,
                    2,
                )
                stats[date_str]["statements"]["status"][payment_status][
                    "revenue_amount"
                ] = round(
                    stats[date_str]["statements"]["status"][payment_status][
                        "revenue_amount"
                    ]
                    + revenue_amount,
                    2,
                )
                stats[date_str]["statements"]["status"]["TOTAL"][
                    "settlement_amount"
                ] = round(
                    stats[date_str]["statements"]["status"]["TOTAL"][
                        "settlement_amount"
                    ]
                    + settlement_amount,
                    2,
                )
                stats[date_str]["statements"]["status"][payment_status][
                    "settlement_amount"
                ] = round(
                    stats[date_str]["statements"]["status"][payment_status][
                        "settlement_amount"
                    ]
                    + settlement_amount,
                    2,
                )
                stats[date_str]["statements"]["status"]["TOTAL"]["fee_amount"] = round(
                    stats[date_str]["statements"]["status"]["TOTAL"]["fee_amount"]
                    + fee_amount,
                    2,
                )
                stats[date_str]["statements"]["status"][payment_status][
                    "fee_amount"
                ] = round(
                    stats[date_str]["statements"]["status"][payment_status][
                        "fee_amount"
                    ]
                    + fee_amount,
                    2,
                )
                stats[date_str]["statements"]["status"]["TOTAL"][
                    "adjustment_amount"
                ] = round(
                    stats[date_str]["statements"]["status"]["TOTAL"][
                        "adjustment_amount"
                    ]
                    + adjustment_amount,
                    2,
                )
                stats[date_str]["statements"]["status"][payment_status][
                    "adjustment_amount"
                ] = round(
                    stats[date_str]["statements"]["status"][payment_status][
                        "adjustment_amount"
                    ]
                    + adjustment_amount,
                    2,
                )

                shop_id = str(statement["shop"]["id"])
                shop_entry = next(
                    (
                        p
                        for p in stats[date_str]["statements"]["shops"]
                        if p["shop_id"] == shop_id
                    ),
                    None,
                )
                if not shop_entry:
                    stats[date_str]["statements"]["shops"].append(
                        {
                            "shop_id": shop_id,
                            "shop_name": str(statement["shop"]["name"]),
                            "shop_owner_id": str(statement["shop_owner"]["id"]),
                            "shop_owner_name": str(statement["shop_owner"]["username"]),
                            "status": {
                                "TOTAL": {
                                    "revenue_amount": revenue_amount,
                                    "settlement_amount": settlement_amount,
                                    "fee_amount": fee_amount,
                                    "adjustment_amount": adjustment_amount,
                                },
                                payment_status: {
                                    "revenue_amount": revenue_amount,
                                    "settlement_amount": settlement_amount,
                                    "fee_amount": fee_amount,
                                    "adjustment_amount": adjustment_amount,
                                },
                            },
                        }
                    )
                else:
                    shop_entry["status"].setdefault(
                        payment_status,
                        {
                            "revenue_amount": 0,
                            "settlement_amount": 0,
                            "fee_amount": 0,
                            "adjustment_amount": 0,
                        },
                    )
                    shop_entry["status"]["TOTAL"]["revenue_amount"] = round(
                        shop_entry["status"]["TOTAL"]["revenue_amount"]
                        + revenue_amount,
                        2,
                    )
                    shop_entry["status"]["TOTAL"]["settlement_amount"] = round(
                        shop_entry["status"]["TOTAL"]["settlement_amount"]
                        + settlement_amount,
                        2,
                    )
                    shop_entry["status"]["TOTAL"]["fee_amount"] = round(
                        shop_entry["status"]["TOTAL"]["fee_amount"] + fee_amount, 2
                    )
                    shop_entry["status"]["TOTAL"]["adjustment_amount"] = round(
                        shop_entry["status"]["TOTAL"]["adjustment_amount"]
                        + adjustment_amount,
                        2,
                    )
                    shop_entry["status"][payment_status]["revenue_amount"] = round(
                        shop_entry["status"][payment_status]["revenue_amount"]
                        + revenue_amount,
                        2,
                    )
                    shop_entry["status"][payment_status]["settlement_amount"] = round(
                        shop_entry["status"][payment_status]["settlement_amount"]
                        + settlement_amount,
                        2,
                    )
                    shop_entry["status"][payment_status]["fee_amount"] = round(
                        shop_entry["status"][payment_status]["fee_amount"] + fee_amount,
                        2,
                    )
                    shop_entry["status"][payment_status]["adjustment_amount"] = round(
                        shop_entry["status"][payment_status]["adjustment_amount"]
                        + adjustment_amount,
                        2,
                    )
                stats[date_str]["statements"]["shops"] = sorted(
                    stats[date_str]["statements"]["shops"],
                    key=lambda x: x["status"]["TOTAL"]["revenue_amount"],
                    reverse=True,
                )

            formatted_stats = []
            for date, data in stats.items():
                formatted_stats.append(
                    {
                        "date": date,
                        "statements": data["statements"],
                        # "products": data["products"],
                    }
                )

            formatted_stats = sorted(
                formatted_stats, key=lambda x: x["date"], reverse=True
            )

            return JsonResponse({"status": "success", "data": formatted_stats})
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)})


class StatisticsApi(APIView):
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Unauthorized", content_type="text/plain")
            pagination, filters, sorts = get_pagination(
                request,
                ["create_time", "order_status", "shop_id", "user_id"],
            )
            user = request.user
            all_order_filters = {
                "shop_id": filters.get("shop_id", {}),
                "user_id": filters.get("user_id", {}),
                "create_time": filters.get("create_time", {}),
                "order_status": filters.get(
                    "order_status",
                    {
                        "$in": "UNPAID,ON_HOLD,PARTIALLY_SHIPPING,AWAITING_SHIPMENT,AWAITING_COLLECTION,IN_TRANSIT,"
                        "DELIVERED,COMPLETED,CANCELLED"
                    },
                ),
            }
            orders = get_all_order(user=user, filters=all_order_filters)

            # with open("data.json", "r", encoding="utf-8") as file:
            #     orders = json.load(file)
            # orders = orders["data"]
            stats = {}
            for order in orders:
                date_str = datetime.fromtimestamp(
                    order["create_time"], pytz.utc
                ).strftime("%Y-%m-%d")
                if date_str not in stats:
                    stats[date_str] = {
                        "orders": {
                            "status": {},
                            "payments": {},
                            "shops": [],
                            "shop_owner": {},
                        },
                        "products": [],
                    }

                order_status = order["status"]

                stats[date_str]["orders"]["status"].setdefault("TOTAL", 0)
                stats[date_str]["orders"]["status"].setdefault(order_status, 0)
                stats[date_str]["orders"]["status"]["TOTAL"] += 1
                stats[date_str]["orders"]["status"][order_status] += 1

                for item in order["line_items"]:
                    product_id = str(item["product_id"])
                    product_name = item["product_name"]
                    sku_image = item["sku_image"]
                    product_entry = next(
                        (
                            p
                            for p in stats[date_str]["products"]
                            if p["product_id"] == product_id
                        ),
                        None,
                    )
                    if not product_entry:
                        stats[date_str]["products"].append(
                            {
                                "product_id": product_id,
                                "product_name": product_name,
                                "sku_image": sku_image,
                                "status": {"TOTAL": 1, order_status: 1},
                                "sale_price": {
                                    "TOTAL": round(float(item["sale_price"]), 2),
                                    order_status: round(float(item["sale_price"]), 2),
                                },
                            }
                        )
                    else:
                        product_entry["status"].setdefault(order_status, 0)
                        product_entry["status"]["TOTAL"] += 1
                        product_entry["status"][order_status] += 1
                        product_entry["sale_price"].setdefault(order_status, 0)
                        product_entry["sale_price"]["TOTAL"] = round(
                            product_entry["sale_price"]["TOTAL"]
                            + float(item["sale_price"]),
                            2,
                        )
                        product_entry["sale_price"][order_status] = round(
                            product_entry["sale_price"][order_status]
                            + float(item["sale_price"]),
                            2,
                        )
                stats[date_str]["products"] = sorted(
                    stats[date_str]["products"],
                    key=lambda x: x["status"]["TOTAL"],
                    reverse=True,
                )

                shop_id = str(order["shop"]["id"])
                shop_entry = next(
                    (
                        p
                        for p in stats[date_str]["orders"]["shops"]
                        if p["shop_id"] == shop_id
                    ),
                    None,
                )
                if not shop_entry:
                    stats[date_str]["orders"]["shops"].append(
                        {
                            "shop_id": shop_id,
                            "shop_name": str(order["shop"]["name"]),
                            "shop_owner_id": str(order["shop_owner"]["id"]),
                            "shop_owner_name": str(order["shop_owner"]["username"]),
                            "status": {"TOTAL": 1, order_status: 1},
                        }
                    )
                else:
                    shop_entry["status"].setdefault(order_status, 0)
                    shop_entry["status"]["TOTAL"] += 1
                    shop_entry["status"][order_status] += 1
                stats[date_str]["orders"]["shops"] = sorted(
                    stats[date_str]["orders"]["shops"],
                    key=lambda x: x["status"]["TOTAL"],
                    reverse=True,
                )

                stats[date_str]["orders"]["payments"].setdefault("total_amount", {})
                stats[date_str]["orders"]["payments"]["total_amount"].setdefault(
                    "TOTAL", 0
                )
                stats[date_str]["orders"]["payments"]["total_amount"].setdefault(
                    order_status, 0
                )
                stats[date_str]["orders"]["payments"]["total_amount"]["TOTAL"] = round(
                    stats[date_str]["orders"]["payments"]["total_amount"]["TOTAL"]
                    + float(order["payment"]["total_amount"]),
                    2,
                )
                stats[date_str]["orders"]["payments"]["total_amount"][
                    order_status
                ] = round(
                    stats[date_str]["orders"]["payments"]["total_amount"][order_status]
                    + float(order["payment"]["total_amount"]),
                    2,
                )

            formatted_stats = []
            for date, data in stats.items():
                formatted_stats.append(
                    {
                        "date": date,
                        "orders": data["orders"],
                        "products": data["products"],
                    }
                )

            formatted_stats = sorted(
                formatted_stats, key=lambda x: x["date"], reverse=True
            )
            return JsonResponse({"status": "success", "data": formatted_stats})
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)})
