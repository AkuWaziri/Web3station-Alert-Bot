def main():

    print("======================================")
    print("WEB3STATION")
    print("======================================")
    print(now())

    seen = set(load_json(SEEN_FILE, []))
    topic_history = load_json(TOPIC_FILE, [])

    # --------------------------------------------------------
    # COLLECT
    # --------------------------------------------------------

    collectors = [
        ("CoinMarketCap", fetch_coinmarketcap),
        ("CoinGecko", fetch_coingecko),
        ("News", fetch_news),
        ("Reddit", fetch_reddit),
        ("LunarCrush", fetch_lunarcrush),
        ("Neynar", fetch_neynar),
        ("Sorsa", fetch_sorsa),
        ("GitHub", fetch_github),
    ]

    all_items = []

    for name, function in collectors:

        print(f"\n[COLLECT] {name}")

        try:
            items = function()

            print(f"[{name}] {len(items)} signals")

            all_items.extend(items)

        except Exception as exc:

            print(f"[{name} ERROR] {exc}")

    print(f"\nTOTAL SIGNALS: {len(all_items)}")

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique = []
    local_ids = set()

    for item in all_items:

        item_id = item.get("id")

        if not item_id:
            continue

        if item_id in seen:
            continue

        if item_id in local_ids:
            continue

        local_ids.add(item_id)

        item["_score"] = relevance_score(item)

        unique.append(item)

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    unique.sort(
        key=lambda x: x.get("_score", 0),
        reverse=True
    )

    print(f"NEW SIGNALS: {len(unique)}")

    # --------------------------------------------------------
    # SELECT
    #
    # IMPORTANT:
    # Do NOT require score >= 2.
    # If a source gave us a signal, let the editor decide.
    # --------------------------------------------------------

    selected = []

    source_count = {}

    for item in unique:

        source = item.get("source", "Unknown")

        source_count.setdefault(source, 0)

        if source_count[source] >= 1:
            continue

        selected.append(item)

        source_count[source] += 1

    print(f"SELECTED REPORTS: {len(selected)}")

    # --------------------------------------------------------
    # EMERGENCY TELEGRAM TEST
    #
    # This proves whether Telegram itself works.
    # --------------------------------------------------------

    test_message = (
        "🧠 WEB3STATION\n\n"
        "BOT TEST\n\n"
        "The bot reached the Telegram delivery stage.\n\n"
        f"Time: {now()}"
    )

    print("\n[TELEGRAM TEST] Sending test message...")

    telegram_test = send_telegram(test_message)

    if telegram_test:
        print("[TELEGRAM TEST] SUCCESS")
    else:
        print("[TELEGRAM TEST] FAILED")

    # --------------------------------------------------------
    # PROCESS SIGNALS
    # --------------------------------------------------------

    successful_ids = []

    for item in selected:

        print("\n--------------------------------------")

        print(
            f"SOURCE: {item.get('source')}"
        )

        print(
            f"TITLE: {item.get('title')}"
        )

        print(
            f"SCORE: {item.get('_score', 0)}"
        )

        # ----------------------------------------------------
        # TRY GROQ
        # ----------------------------------------------------

        editorial = None

        try:

            editorial = groq_edit(item)

        except Exception as exc:

            print(
                f"[GROQ EXCEPTION] {exc}"
            )

        # ----------------------------------------------------
        # IF GROQ FAILS, STILL SEND THE SIGNAL
        # ----------------------------------------------------

        if editorial:

            message = format_message(
                item,
                editorial
            )

        else:

            print(
                "[GROQ] Editorial failed."
            )

            print(
                "[FALLBACK] Sending raw signal to Telegram."
            )

            message = (
                "🧠 WEB3STATION\n\n"

                f"SOURCE\n"
                f"{item.get('source', 'Unknown')}\n\n"

                f"CATEGORY\n"
                f"{item.get('title', 'Crypto Signal')}\n\n"

                f"ANGLE\n"
                f"Editorial AI unavailable for this scan.\n\n"

                f"DRAFT\n"
                f"{item.get('text', '')[:1800]}\n\n"

                f"SOURCE\n"
                f"{item.get('url', '')}"
            )

        # Telegram max is 4096 characters.
        message = message[:3900]

        # ----------------------------------------------------
        # SEND TELEGRAM
        # ----------------------------------------------------

        print("[TELEGRAM] Sending report...")

        sent = send_telegram(message)

        if sent:

            print("[SENT]")

            successful_ids.append(
                item["id"]
            )

            if editorial:

                topic_history.append({

                    "timestamp": now(),

                    "source":
                        item.get("source"),

                    "category":
                        editorial.get(
                            "category"
                        ),

                    "title":
                        item.get("title")

                })

        else:

            print(
                "[NOT SENT] Signal will be retried."
            )

    # --------------------------------------------------------
    # SAVE SUCCESSFULLY SENT SIGNALS
    # --------------------------------------------------------

    for item_id in successful_ids:

        seen.add(item_id)

    save_json(
        SEEN_FILE,
        list(seen)[-5000:]
    )

    save_json(
        TOPIC_FILE,
        topic_history[-500:]
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print("\n======================================")
    print("RUN COMPLETE")
    print("======================================")

    print(
        f"Signals collected: {len(all_items)}"
    )

    print(
        f"New signals: {len(unique)}"
    )

    print(
        f"Selected: {len(selected)}"
    )

    print(
        f"Reports sent: {len(successful_ids)}"
    )

    print(
        f"Telegram test: {'PASS' if telegram_test else 'FAIL'}"
    )

    print("======================================")
