# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import scrapy
from scrapy.crawler import CrawlerProcess

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())




class ImmoscoutItem(scrapy.Item):
    immo_id = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    address = scrapy.Field()
    city = scrapy.Field()
    zip_code = scrapy.Field()
    district = scrapy.Field()
    contact_name = scrapy.Field()
    media_count = scrapy.Field()
    lat = scrapy.Field()
    lng = scrapy.Field()
    sqm = scrapy.Field()
    rent = scrapy.Field()
    rooms = scrapy.Field()
    extra_costs = scrapy.Field()
    kitchen = scrapy.Field()
    balcony = scrapy.Field()
    garden = scrapy.Field()
    private = scrapy.Field()
    area = scrapy.Field()
    cellar = scrapy.Field()
    time_dest = scrapy.Field()
    time_dest2 = scrapy.Field()
    time_dest3 = scrapy.Field()


class ImmoscoutSpider(scrapy.Spider):
    name = "immoscout"
    allowed_domains = ["immobilienscout24.de"]
    start_urls = [
        "https://www.immobilienscout24.de/Suche/de/nordrhein-westfalen/koeln/wohnung-mieten"
    ]
    script_xpath = './/script[contains(., "IS24.resultList")]'
    next_xpath = '//div[@id = "pager"]/div/a/@href'

    def parse(self, response):
        print(response.url)

        script = response.xpath(self.script_xpath).get()
        if script is None:
            self.logger.warning("Keine Ergebnisdaten im Seitenquelltext gefunden: %s", response.url)
            return

        for line in script.split("\n"):
            if line.strip().startswith("resultListModel"):
                immo_json = json.loads(line.strip()[17:-1])
                results = immo_json["searchResponseModel"]["resultlist.resultlist"]["resultlistEntries"][0]["resultlistEntry"]

                # ImmoScout kann bei genau einem Treffer statt einer Liste ein einzelnes Objekt liefern.
                if isinstance(results, dict):
                    results = [results]

                for result in results:
                    item = ImmoscoutItem()
                    data = result["resultlist.realEstate"]
                    address = data.get("address", {})

                    item["immo_id"] = data.get("@id")
                    item["url"] = response.urljoin("/expose/" + str(data.get("@id")))
                    item["title"] = data.get("title")
                    item["address"] = " ".join(
                        part for part in (address.get("street"), address.get("houseNumber")) if part
                    ) or None
                    item["city"] = address.get("city")
                    item["zip_code"] = address.get("postcode")
                    item["district"] = address.get("quarter")

                    price = data.get("price", {}).get("value")
                    item["rent"] = price
                    item["sqm"] = data.get("livingSpace")
                    item["rooms"] = data.get("numberOfRooms")

                    calculated_price = data.get("calculatedPrice", {}).get("value")
                    if calculated_price is not None and price is not None:
                        item["extra_costs"] = calculated_price - price

                    for source_key, item_key in (
                        ("builtInKitchen", "kitchen"),
                        ("balcony", "balcony"),
                        ("garden", "garden"),
                        ("privateOffer", "private"),
                        ("plotArea", "area"),
                        ("cellar", "cellar"),
                    ):
                        if source_key in data:
                            item[item_key] = data[source_key]

                    contact = data.get("contactDetails", {})
                    first_name = contact.get("firstname")
                    last_name = contact.get("lastname")
                    item["contact_name"] = " ".join(
                        name for name in (first_name, last_name) if name
                    ) or None

                    attachments = data.get("galleryAttachments", {}).get("attachment", [])
                    item["media_count"] = len(attachments) if isinstance(attachments, list) else 1

                    coordinates = address.get("wgs84Coordinate", {})
                    item["lat"] = coordinates.get("latitude")
                    item["lng"] = coordinates.get("longitude")
                    yield item

        next_page_list = response.xpath(self.next_xpath).getall()
        if next_page_list:
            next_page = response.urljoin(next_page_list[-1])
            print("Scraping next page", next_page)
            yield scrapy.Request(next_page, callback=self.parse)


def main():
    process = CrawlerProcess({
        "FEEDS": {
            "wohnungen.json": {"format": "json"}
        }
    })
    process.crawl(ImmoscoutSpider)
    process.start()


if __name__ == "__main__":
    main()
