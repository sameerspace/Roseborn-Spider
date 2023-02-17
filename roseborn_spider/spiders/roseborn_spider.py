import json


from scrapy import Request
from scrapy.spiders import Spider
from w3lib.html import remove_tags

from roseborn_spider.items import RosebornSpiderItem


class RoseBornSpider(Spider):
    name = 'roseborn'
    start_urls = ['https://roseborn.com/']
    allowed_domains = ['roseborn.com']

    def parse(self, response):
        category_css = 'div.category-link-container div.category-link a::attr(href)'
        category_links = response.css(category_css).getall()
        for url in category_links:
            yield Request(url, self.parse_links)

    def parse_links(self, response):
        urls = response.css('div.products div a::attr(href)').getall()
        for url in urls:
            yield Request(url, self.parse_product)
        next_page_url = response.css('.next.page-numbers::attr(href)').get()
        if next_page_url:
            yield Request(next_page_url, self.parse_links)

    def parse_product(self, response):
        product_css = 'script[type="application/ld+json"]::text'
        prod_json = response.css(product_css).get()
        raw_product = json.loads(prod_json)
        garment = RosebornSpiderItem()

        garment['retailer_sku'] = self.parse_retailer_sku(raw_product)
        garment['gender'] = self.parse_gender()
        garment['category'] = self.parse_category(response)
        garment['brand'] = self.parse_brand(raw_product)
        garment['url'] = response.url
        garment['url_original'] = response.url
        garment['name'] = self.parse_name(raw_product)
        garment['description'] = self.parse_description(response)
        garment['care'] = self.parse_care(response)
        garment['image_urls'] = self.parse_images(response)
        garment['skus'] = self.parse_variants(response, raw_product)

        yield garment

    def parse_retailer_sku(self, raw_product):
        return raw_product['sku']

    def parse_gender(self):
        return 'Male'

    def parse_category(self, response):
        return response.url.split('/')[4]

    def parse_brand(self, raw_product):
        return raw_product['offers'][0]['seller']['name']

    def parse_name(self, raw_product):
        return raw_product['name']

    def parse_care(self, response):
        text = response.css('div.col-md-4.product-col-wash-size ul').get()
        care = remove_tags(text).replace('\xa0', ' ').split('\n')
        return list(filter(None, care))

    def parse_images(self, response):
        img_css = 'div.swiper-wrapper img::attr(data-lazy-src)'
        image_links = response.css(img_css).getall()
        return image_links

    def parse_prices(self, response):
        prices = response.css('div.summary.entry-summary bdi::text').getall()
        if len(prices) > 1:
            prev_price = int(prices[0].replace(',', '').replace('.', ''))/100
            price = int(prices[1].replace(',', '').replace('.', ''))/100
        else:
            prev_price = ""
            price = int(prices[0].replace(',', '').replace('.', ''))/100
        return {
            'price': price,
            'prev_price': prev_price
        }

    def parse_description(self, response):
        description_css = 'div.col-md-4.product-col-details ul li::text'
        return response.css(description_css).getall()

    def parse_variants(self, response, product_data):
        sku_css = 'form.variations_form.cart::attr(data-product_variations)'
        raw_product = response.css(sku_css).get()
        price_details = self.parse_prices(response)
        if raw_product:
            products = json.loads(raw_product)
            skus = {}
            for product in products:
                sku_variant = {
                    'colour': product_data['name'].split(' ')[0],
                    'price': price_details['price'],
                    'currency': product_data['offers'][0]['priceCurrency'],
                    'previous_prices': [price_details['prev_price']],
                    'size': product['attributes']['attribute_pa_size'],
                    'out_of_stock': not product['is_in_stock'],
                    'sku_id': product['sku'],
                }
                skus[product['sku']] = sku_variant
            return skus
        return []
