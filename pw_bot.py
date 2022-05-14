##
# Scrapes lexicographical data from duden.de for any given word.
# Creates the corresponding Json file
# Author: Alp Bulut
#

from playwright.async_api import async_playwright
import asyncio
import json

word = input("Stichwort: ")
data = {}
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # Open new page
        page = await context.new_page()
        # Lower timeout value
        page.set_default_timeout(5000)
        # Go to https://www.duden.de/
        await page.goto("https://www.duden.de/")
        # Accept Cookies
        await page.frame_locator("#sp_message_iframe_622759").locator(
            "text=AKZEPTIEREN").first.click()
        # Fill search bar
        await page.locator("[placeholder=\"Stichwort\"]").fill(word)
        # Click Enter
        await page.locator("[placeholder=\"Stichwort\"]").press("Enter")
        # Check if such word exists, if not; close the browser
        try:
            await page.locator(
                'section.vignette:nth-child(2) > h2:nth-child(1)' +
                ' > a:nth-child(1) > strong:nth-child(1)'
                ).click()
        except Exception:
            print('Timeout')
            await browser.close()
        # Try to pass irregular google ad during navigation
        try:
            await page.frame_locator(
                "[id=\"google_ads_iframe_\\/53015287\\" +
                ",224194632\\/duden\\.de_interstitial_0\"]"
                ).frame_locator(
                    "iframe[name=\"ad_iframe\"]"
                    ).locator(
                        "[aria-label=\"Anzeige schließen\"]").click()
        except:
            pass

        # Get the title of the word page
        title_el = await page.query_selector('div.lemma')
        title = await title_el.inner_text()

        # Get basic info about word
        all_desc = await page.query_selector_all('dl.tuple')
        title_data = {}

        for item in all_desc:
            tuple_key_el = await item.query_selector('dt.tuple__key')
            tuple_key = await tuple_key_el.inner_text()
            tuple_key = tuple_key.split(':')[0]
            tuple_val_el = await item.query_selector('dd.tuple__val')
            tuple_val = await tuple_val_el.inner_text()

            if tuple_key == "Wortart" or tuple_key == "H\u00e4ufigkeit":
                # Convert Haufigkeit graph into rational number
                if tuple_key == 'H\u00e4ufigkeit':
                    tuple_key = 'Haufigkeit'
                    tuple_val = str(len(tuple_val.split('\n')[0])) + '/5'

                title_data[tuple_key] = tuple_val
        data[title] = title_data

        # Check if the word has multiple meanings
        has_multiple_meanings = True
        if await page.query_selector('#bedeutungen') is None:
            has_multiple_meanings = False

        meaning_data = {}
        # Loop for words with multiple meanings
        if has_multiple_meanings:
            all_meaning = await page.query_selector_all('li.enumeration__item')

            for item in all_meaning:
                sub_meaning = await item.query_selector_all(
                    'li.enumeration__sub-item')
                if sub_meaning is not None:
                    for sub_item in sub_meaning:
                        meaning_key = await item.get_attribute("id")
                        meaning_key = (meaning_key or '')
                        meaning_key += await sub_item.get_attribute("id")
                        meaning_el = await sub_item.query_selector(
                            'div.enumeration__text')
                        if meaning_el is None:
                            continue
                        meaning = await meaning_el.inner_text()
                        meaning_data[meaning_key] = meaning

                # For single entries under one of many categories
                meaning_key = await item.get_attribute("id")
                if meaning_key is not None:
                    meaning_el = await item.query_selector(
                        'div.enumeration__text')
                    if meaning_el is None:
                        continue
                    meaning = await meaning_el.inner_text()
                    meaning_data[meaning_key] = meaning

        # Process words with only single meaning
        else:
            all_meaning = await page.query_selector(
                '#bedeutung > p:nth-child(2)')
            meaning = await all_meaning.inner_text()
            meaning_data['Bedeutung-1'] = meaning
        data['Bedeutungen'] = meaning_data

        # Get synonym data of the word
        all_synonym = await page.query_selector(
            'div.division:nth-child(5) > ul:nth-child(2) > li:nth-child(1)')
        if all_synonym is not None:
            synonym_data = await all_synonym.inner_text()
            data['Synonyme'] = synonym_data

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except TypeError:
        print('Cookies Error, Try Again')
    except TimeoutError:
        print("kein solches Wort oder ähnliches")
with open(word + '.json', 'w') as json_file:
    json.dump(data, json_file, indent=4)
    print("The json file is created")
