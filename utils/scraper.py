import time

def fetch_seat_statuses(page, url, data_search_ids):
    """
    Fetches seat statuses from an e5489 result page.
    :param page: Playwright page object.
    :param url: URL to check.
    :param data_search_ids: List of data-search-id strings to look for.
    :return: A dictionary mapping data-search-id to its status ("〇", "△", "×", "情報なし", "取得タイムアウト", etc.).
    """
    max_retries = 5
    retry_count = 0
    results = {ds_id: "取得タイムアウト" for ds_id in data_search_ids}

    while retry_count < max_retries:
        try:
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            
            content = page.content()
            if "混雑中" in content or "20100801" in content:
                retry_count += 1
                time.sleep(2)
                continue
                
            # Try waiting for search id element, if it times out just proceed (it might legitimately be missing)
            try:
                page.wait_for_selector("td[data-search-id]", timeout=5000)
            except Exception:
                pass
                
            for ds_id in data_search_ids:
                try:
                    selector = f"td[data-search-id='{ds_id}'] img"
                    img_elements = page.query_selector_all(selector)
                    
                    status = "情報なし"
                    if img_elements:
                        for img in img_elements:
                            alt_text = img.get_attribute("alt")
                            if alt_text:
                                if alt_text == "空席あり":
                                    status = "〇"
                                elif alt_text == "空席残りわずか":
                                    status = "△"
                                elif alt_text == "残席なし" or alt_text == "座席なし":
                                    status = "×"
                                else:
                                    status = alt_text
                                break
                    results[ds_id] = status
                except Exception:
                    results[ds_id] = "取得エラー"
                    
            return results
                
        except Exception:
            retry_count += 1
            time.sleep(2)
            
    return results
