from playwright.sync_api import sync_playwright
import time
import os
import json
from datetime import datetime
import re
from bs4 import BeautifulSoup

def html_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Initialize the result dictionary
    result = {}

    # Get the date from the first strong tag
    date_row = soup.find('tr', class_='date-row')
    if date_row:
        date = date_row.find('strong').text.strip()
        result[date] = {}
    else:
        return {}

    # Find all category rows
    category_rows = soup.find_all('tr', class_='category-row')

    current_category = None

    for category_row in category_rows:
        category_name = category_row.find('strong').text.strip() + "</span>"
        result[date][category_name] = []
        current_category = category_name

        # Find all event rows that follow this category row until the next category row
        next_row = category_row.find_next_sibling('tr')
        while next_row and 'category-row' not in next_row.get('class', []):
            if 'event-row' in next_row.get('class', []):
                event_time = next_row.find('div', class_='event-time').find('strong').text.strip()
                event_info = next_row.find('div', class_='event-info').text.strip()

                event_data = {
                    "time": event_time,
                    "event": event_info,
                    "channels": []
                }

                # Find the channel row that follows this event row
                channel_row_id = f"channels-{date}-{current_category}-{len(result[date][current_category])}"
                channel_row = soup.find('tr', id=channel_row_id)

                if channel_row:
                    channel_links = channel_row.find_all('a', class_='channel-button-small')
                    for link in channel_links:
                        href = link['href']
                        channel_id_match = re.search(r'stream-(\d+)\.php', href)
                        if channel_id_match:
                            channel_id = channel_id_match.group(1)
                            channel_name = link.text.strip()
                            # Remove the channel ID from the channel name if it's in parentheses
                            channel_name = re.sub(r'\s*\(CH-\d+\)$', '', channel_name)

                            event_data["channels"].append({
                                "channel_name": channel_name,
                                "channel_id": channel_id
                            })

                result[date][current_category].append(event_data)

            next_row = next_row.find_next_sibling('tr')
            if not next_row or ('category-row' in next_row.get('class', [])):
                break

    return result

def extract_schedule_container():
    url = "https://daddylive.mp/"
    html_output = "main_schedule_container.html"
    json_output = "daddyliveSchedule.json"

    print(f"Accesso alla pagina {url} per estrarre il main-schedule-container...")

    with sync_playwright() as p:
        # Lancia un browser Chromium in background
        browser = p.chromium.launch(headless=True)

        # Configura il contesto con un user agent realistico
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        )

        # Crea una nuova pagina
        page = context.new_page()

        try:
            # Naviga alla URL
            print("Navigazione alla pagina...")
            page.goto(url)

            # Attendi per il caricamento dinamico del contenuto
            print("Attesa per il caricamento completo...")
            page.wait_for_timeout(10000)  # 10 secondi

            # Estrai il contenuto HTML
            schedule_content = page.evaluate("""() => {
                const container = document.getElementById('main-schedule-container');
                return container ? container.outerHTML : '';
            }""")

            if not schedule_content:
                print("AVVISO: main-schedule-container trovato ma è vuoto o non presente!")
                return False

            # Salva l'HTML
            with open(html_output, "w", encoding="utf-8") as f:
                f.write(schedule_content)

            print(f"Contenuto HTML salvato in {html_output} ({len(schedule_content)} caratteri)")

            # Converti HTML in JSON
            print("Conversione HTML in formato JSON...")
            json_data = html_to_json(schedule_content)

            # Salva i dati JSON
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=4)

            print(f"Dati JSON salvati in {json_output}")

            # Cattura screenshot per debug
            page.screenshot(path="schedule_screenshot.png")

            # Chiudi il browser
            browser.close()

            return True

        except Exception as e:
            print(f"ERRORE: {str(e)}")
            # Cattura uno screenshot in caso di errore per debug
            try:
                page.screenshot(path="error_screenshot.png")
                print("Screenshot dell'errore salvato in error_screenshot.png")
            except:
                pass
            return False

if __name__ == "__main__":
    success = extract_schedule_container()
    # Imposta il codice di uscita in base al successo dell'operazione
    # Utile per i sistemi CI che controllano i codici di uscita
    if not success:
        exit(1)
