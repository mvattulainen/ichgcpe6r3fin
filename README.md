# ICH E6(R3) – suomenkielinen tietopohja

Versioitu, kaksikielinen ja koneellisesti luettava tietopohja Fimean tarkistamasta epävirallisesta ICH E6(R3) -käännöksestä ja EMA:n englanninkielisestä Step 5 -lähteestä.

## Rakenne

- `sources/`: muuttamattomat PDF-lähteet ja SHA-256-manifesti
- `data/`: kanoniset JSON-aineistot
- `content/`: aineistoista tuotetut Obsidian- ja Quartz-sivut
- `reports/`: kattavuus-, kohdistus- ja laadunvarmistusraportit
- `scripts/`: deterministinen poiminta- ja validointiputki

## Paikallinen käyttö

1. Asenna Python-riippuvuudet: `python -m pip install -r requirements.txt`
2. Asenna sivustoriippuvuudet: `npm ci`
3. Luo ja tarkista tietopohja: `npm run generate` ja `npm run validate`
4. Koosta sivusto: `npm run build`

`sources/manifest.yaml` tarkistetaan ennen jokaista poimintaa. Putki pysähtyy, jos lähde puuttuu tai SHA-256 ei täsmää.

## Manuaalisesti ylläpidettävä etusivu

Sivuston etusivua muokataan tiedostossa `content/index.md`. Generointiputki säilyttää tämän tiedoston muuttamattomana eikä kirjoita sitä uudelleen. Muut `content/`-hakemiston sivut tuotetaan automaattisesti.

`npm run validate` tarkistaa lisäksi, että julkaistavaksi tarkoitettu suomen- ja englanninkielinen lähdeteksti vastaa PDF-poimintaa. Tulokset tallennetaan tiedostoon `reports/source-exactness-report.md`.

## Lähde- ja tulkintahuomautus

Suomenkielinen käännös on epävirallinen ja englanninkielinen lähde oikeudellisesti sitova. Lähdeteksti säilytetään erillään automaattisesti johdetuista roolinäkymistä, velvoitteista ja havainnollistavista näyttöesimerkeistä. Johdettu aineisto odottaa asiantuntijan tarkistusta.

Quartz on lukittu pääversioon 5 (`package.json`, `package-lock.json`) ja lähdekoodin pohjana on upstream-commit `9cf87ff1c248a8ca551093214b0fec3b31415009`.
