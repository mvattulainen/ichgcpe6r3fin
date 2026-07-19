---
title: "Kehittäjille ja tekoälyagenteille"
id: "ich-e6-r3-machine-interface-guide"
content_type: "documentation"
language: "fi"
lang: "fi"
schema_type: "TechArticle"
classification: "project_documentation"
publish: true
permalink: "/kehittajille-ja-agenteille/"
---

Tämä sivusto julkaisee ihmisten luettavan verkkosisällön rinnalla staattisen, vain luku -tyyppisen konerajapinnan. Rajapinta ei ole palvelimella suoritettava API: kaikki vastaukset ovat ennalta muodostettuja tiedostoja, jotka GitHub Pages palauttaa tavallisella HTTP `GET` -pyynnöllä.

> [!important] Auktoriteetti ja tarkistustila
> Englanninkielinen ICH E6(R3) -lähde on auktoritatiivinen. Suomenkielinen aineisto on epävirallinen käännös. Kaikki tulkitseva, automaattisesti johdettu aineisto on merkitty arvoilla `classification: derived` ja `review_status: pending` eikä sitä tule käyttää yksin kliinisen, oikeudellisen, sääntelyä koskevan tai vaatimustenmukaisuuspäätöksen perusteena.

## Aloituspisteet

- [Agenttien lyhyt aloitusohje](../llms.txt)
- [Korpuksen manifesti](../corpus-manifest.json)
- [Staattisen rajapinnan indeksi](../api/index.json)
- [OpenAPI-kuvaus](../openapi.json)
- [Hakemisto agentin paikallista suodatusta varten](../api/search-index.json)
- [Oikeuksia koskeva koneluettava kuvaus](https://mvattulainen.github.io/ichgcpe6r3fin/rights/rights.json)
- [[miten-sivusto-tukee-tekoalyagentteja|Miten sivusto tukee tekoälyagentteja]]

Perusosoite on:

```text
https://mvattulainen.github.io/ichgcpe6r3fin
```

## Aineistot

Muuttumattomat version `v1` aineistot ovat hakemistossa `/data/v1/`. Hakemiston `/data/latest/` tiedostot ovat siirtyviä mukavuuskopioita, joten pitkäikäisten integraatioiden tulee käyttää ja siteerata `v1`-osoitteita.

Saatavilla ovat asiakirjat, osiot, lausekkeet, suomi–englanti-kohdistukset, sanasto, termikohdistukset, roolit, velvoite-ehdokkaat ja oleelliset tallenteet. Jokainen kokoelma sisältää korpus- ja skeemaversion, tietuetyypin, lukumäärän, tietueet sekä sisältötiivisteen.

Yksittäiset tietueet voi hakea lataamatta koko aineistoa:

```bash
curl https://mvattulainen.github.io/ichgcpe6r3fin/api/v1/sections/ich-e6-r3-a1-2.8.json
curl https://mvattulainen.github.io/ichgcpe6r3fin/api/v1/roles/tutkija.json
```

Lauseketunniste vastaa ihmisen luettavalla sivulla olevaa piilotettua ankkuria. Tämän vuoksi agentti voi hakea täsmällisen kaksikielisen lausekkeen ja ohjata käyttäjän samaan kohtaan HTML-sivulla.

## JSONL-lataukset ja tarkistussummat

Hakemisto `/api/v1/downloads/` sisältää UTF-8- ja NFC-normalisoidut JSONL-tiedostot. Yksi rivi on yksi itsenäinen JSON-tietue, joten aineistoa voi käsitellä suoratoistona tai syöttää RAG-indeksointiin ilman suuren JSON-taulukon lataamista muistiin.

```bash
curl -O https://mvattulainen.github.io/ichgcpe6r3fin/api/v1/downloads/clauses.jsonl
curl -O https://mvattulainen.github.io/ichgcpe6r3fin/api/v1/downloads/checksums.sha256
```

Tarkistussummat käyttävät SHA-256:ta. Yksittäisen tietueen `content_hash` lasketaan deterministisestä esityksestä, josta oma `content_hash`-kenttä on poistettu. Näin agentti voi havaita muutoksen ilman aikaleimoihin tai tiedostojärjestykseen liittyvää kohinaa.

## Skeemat ja OpenAPI

JSON Schema Draft 2020-12 -skeemat julkaistaan hakemistoissa `/schemas/v1/` ja `/schemas/latest/`. Johdetun aineiston skeema sallii tarkistustilaksi vain arvon `pending`.

`/openapi.json` ja `/api/openapi.yaml` kuvaavat staattiset hakupolut OpenAPI 3.1 -muodossa. Kuvaus ei tarkoita, että palvelin käsittelisi polkuparametreja tai kyselyitä. Puuttuva tiedosto voi palauttaa GitHub Pagesin HTML-muotoisen 404-sivun, joten asiakkaan tulee tarkistaa sekä HTTP-tila että `Content-Type`.

## Haku ja turvallinen käyttö

`/api/search-index.json` on paikallisesti suodatettava hakemisto. Sivusto ei tarjoa dynaamista haku-, semanttista haku-, kysymys–vastaus- tai varmennuspalvelua. Agentti vastaa itse kysymyksen tulkinnasta ja vastauksen muodostamisesta.

Suositeltu toimintajärjestys on:

1. lue `llms.txt` ja korpusmanifesti;
2. tarkista korpus- ja skeemaversio;
3. hae lähdekohta tai lauseke;
4. käytä englanninkielistä tekstiä auktoritatiivisena;
5. käsittele johdettua aineistoa vain löytämistä helpottavana ehdokkaana;
6. säilytä tietueen tunniste, lähdekohta, kanoninen URL ja versio viittauksessa;
7. tarkista oikeustiedot ennen aineiston uudelleenjulkaisua, koulutuskäyttöä tai kaupallista käyttöä.

## Muutokset, julkaisut ja ongelmailmoitukset

`/changes.json`, `/feed.xml` ja `/releases/` auttavat havaitsemaan korpusversion muutokset. Julkaisupaketti sisältää koneellisesti käytettävät resurssit offline-käsittelyä varten.

Virheet, puuttuvat kohdistukset ja kehitysehdotukset ilmoitetaan [GitHub-repositorion issue-toiminnolla](https://github.com/mvattulainen/ichgcpe6r3fin/issues). Ilmoitukseen kannattaa liittää korpusversio, tietuetyyppi, vakaa tunniste, URL ja kuvaus havaitusta ongelmasta.
