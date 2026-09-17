import pandas as pd

df = pd.read_csv('sample_data/clean_reviews_land_translated.csv', encoding='utf-8')

manual_translations = {
    9:    ("Very very wow", "translated_manual"),
    12:   ("Good", "already_english_missed"),
    108:  ("Nice view, kids also enjoying", "already_english_missed"),
    124:  ("Note.", "already_english_missed"),
    132:  ("Sunset & night view are amazing❤️", "already_english_missed"),
    280:  ("Great view.", "already_english_missed"),
    400:  ("One good experience", "translated_manual"),          # Dutch
    452:  ("Very enjoyable", "already_english_missed"),
    456:  ("A must visit in langkawi", "already_english_missed"),
    596:  ("Good", "already_english_missed"),
    635:  ("Duriaaaaan, 100 ringgit for 3 Black Thorns, that's the best, right?", "translated_manual_low_confidence"),  # heavy slang, uncertain
    746:  ("The tea plantation is huge. It has a café with views, although there were a lot of people.\n\nAt the tea shop there are 7 different types to try for free, each one better than the last.\n\nThere's also a small free tour of the factory.", "translated_manual"),  # Spanish
    760:  ("good view", "already_english_missed"),
    766:  ("Comfortable & healing..", "translated_manual"),        # Indonesian ("nyaman")
    821:  ("Comfortable", "already_english_missed"),
    855:  ("Good 👍", "already_english_missed"),
    888:  ("Expensive-looking view 😍", "translated_manual"),      # Malay "mahal" = expensive
    909:  ("best", "already_english_missed"),
    969:  ("Kids will enjoy", "already_english_missed"),
    1027: ("bestrttttt", "already_english_missed"),
    1030: ("sooo good!!", "already_english_missed"),
    1031: ("Skyway view", "already_english_missed"),
    1046: ("Azwa good service.", "already_english_missed"),
    1068: ("Amazing", "already_english_missed"),
    1093: ("Guide Nurin was awesome.", "already_english_missed"),
    1137: ("Very beautiful city.", "translated_manual"),          # Bengali
    1155: ("Good", "already_english_missed"),
    1289: ("Perfect😍", "translated_manual"),                     # French
    1298: ("It's Malaysia's icon.", "translated_manual"),         # Malay
    1301: ("Landmark good", "already_english_missed"),
    1338: ("Very beautiful and there's black magic", "translated_manual"),  # Malay/Indonesian, stylized unicode font
    1374: ("Amazing", "already_english_missed"),
    1377: ("MSR", "no_translation_needed"),                       # acronym/initials
    1385: ("Majestic.", "already_english_missed"),
    1395: ("Wonderful view", "already_english_missed"),
    1433: ("4095m", "no_translation_needed"),                     # elevation figure, not linguistic content
    1434: ("besttttt", "already_english_missed"),
    1449: ("Hikking 🥰", "already_english_missed"),
    1456: ("What! amazing !!!", "already_english_missed"),
    1468: ("Amazing hike.\n10/10", "already_english_missed"),
    1482: ("Awesome", "already_english_missed"),
    1494: ("Good", "translated_manual"),                          # Malay/Indonesian "Bagus"
    1498: ("So many rubbish", "already_english_missed"),
    1506: ("very good", "already_english_missed"),
    1539: ("Good view", "already_english_missed"),
    1544: ("niceeeeeee", "already_english_missed"),
    1554: ("Ok", "already_english_missed"),
    1558: ("It's very hot in the sun. You should bring an umbrella.\nYou should come in the morning or evening.", "translated_manual"),  # Burmese
    1576: ("Good", "already_english_missed"),
    1591: ("Really the best", "translated_manual"),               # Malay "Best sangat"
    1602: ("soo good", "already_english_missed"),
    1606: ("soooooo prettyyyy love ittt", "already_english_missed"),
    1607: ("Very beautiful", "translated_manual"),                # Malay
    1635: ("Gooooddd", "already_english_missed"),
    1636: ("good", "already_english_missed"),
    1655: ("Okayyy", "already_english_missed"),
    1662: ("Good so funy", "already_english_missed"),
    1675: ("interesting", "already_english_missed"),
    1682: ("Recommend bringing an umbrella, fan and hat.", "translated_manual"),  # Malay+English
    1683: ("Hot, pls add on fan", "already_english_missed"),
    1688: (
        "One-line review: It looks like a haunted house, and it turns out it really is one?!\n\n"
        "It's a charming castle, but first of all it's too far from downtown. It's more than 15km "
        "from the city center, so it feels like it's practically in a different city, not Ipoh.\n"
        "(In fact, on Google Maps it's actually listed under the place name Batu Gajah, not Ipoh.)\n\n"
        "Most of Ipoh's major tourist spots are like this, but this one's location is especially bad.\n"
        "Even just taking a Grab during the day costs around 30-40 ringgit one way, plus toll fees on top.\n\n"
        "It's open until 10pm, but at night only part of the castle is lit up. It's already a place with "
        "few people on weekdays, and when the lights go out and it starts raining too, it gets even eerier.\n"
        "(That's exactly what happened on the day I visited.)\n\n"
        "It's a castle that an Englishman named Kellie began building for his wife Agnes, but left about "
        "half-finished.\n\n"
        "Naturally, you shouldn't picture European royal palaces or noble castles — it's quite small in "
        "scale as castles go.\n"
        "On top of that, since it was never even completed, you'll be disappointed if you visit expecting "
        "too much.\n\n"
        "In any case, Kellie died of pneumonia in Portugal not long after construction began.\n\n"
        "A long time later, European tourists actually took photos here of what appeared to be Kellie's "
        "ghostly figure, and the castle gained a certain amount of fame from it.\n\n"
        "They say his daughter's ghost also appears in her room, but in fact, Kellie's daughter left "
        "Malaysia safely as a child, holding her father's hand, and grew up to be an adult in Europe.\n"
        "So the academic consensus is that the latter story is just a hoax..\n\n"
        "It's a decent, quiet spot for photos, but on weekdays it's rarely visited, and whether by Grab "
        "or taxi, transportation costs are expensive.\n\n"
        "If you're alone at night, it's an awkward location to wait for a ride back to the city.\n\n"
        "It's a cozy castle, neither too big nor too small, that you can fully explore in about an hour.\n\n"
        "You either buy your entrance ticket online, or buy it in cash from a round-faced local young man "
        "who literally pops out of nowhere like a ghost at a stall in front of the entrance — it's one or "
        "the other.\n"
        "(There's no ticket office. The young man said something like the ticket office went out of "
        "business or was destroyed, but I have doubts whether that's really true.)\n\n"
        "As of August 2025 it's 16 ringgit, and if you pay cash, the young man tells you to take a photo "
        "of a suspicious-looking QR code that's several days old, holds it out, and says this is your ticket.\n\n"
        "It all seems quite suspicious and the price isn't cheap either, but there's no one else around, "
        "so what can you do?\n\n"
        "Part of the castle walls appears to be under repair or being prepared for additional exhibits.\n\n"
        "If you have about half a day, or more, to spare in Ipoh, it's still worth a visit.\n"
        "The fact that a British-style castle still remains in Southeast Asia makes it fairly unique, but "
        "considering the huge round-trip taxi fare, the correspondingly long travel time, and the shady, "
        "not-cheap entrance ticket, it's honestly not an easy place to recommend visiting..",
        "translated_manual",
    ),
    1743: ("Awesome", "already_english_missed"),
    1761: ("Better skip.", "already_english_missed"),
}

for idx, (translation, status) in manual_translations.items():
    df.at[idx, 'text'] = translation
    df.at[idx, 'translation_status'] = status

df.to_csv('sample_data/clean_reviews_land_translated.csv', index=False, encoding='utf-8')

remaining = df[df['translation_status'] == 'untranslated_no_method_available']
print(f"{len(remaining)} rows still untranslated (should be 0).")
print(df['translation_status'].value_counts())