---
title: "Miten sivusto tukee tekoälyagentteja"
id: "ich-e6-r3-ai-agent-support-summary"
content_type: "documentation"
language: "fi"
lang: "fi"
schema_type: "TechArticle"
classification: "project_documentation"
publish: true
permalink: "/kehittajille-ja-agenteille/miten-sivusto-tukee-tekoalyagentteja/"
---

Tekoälyagentti tarvitsee verkkosivustolta enemmän kuin ihmisen silmälle selkeän ulkoasun. Sen on löydettävä aineisto, tunnistettava mitä kukin tiedosto tarkoittaa, erotettava lähde tulkinnasta, pystyttävä hakemaan täsmällinen kohta ja säilytettävä viittaus vastauksessaan. Tämä sivusto tukee näitä tehtäviä julkaisemalla saman ICH E6(R3) -aineiston sekä ihmisten luettavina sivuina että rakenteisina, koneellisesti noudettavina tiedostoina.

## 1/2: Löytäminen, hakeminen ja lähteisiin palaaminen

Agentin ensimmäinen ongelma on löytää oikea aloituspiste. Sivuston `llms.txt` antaa lyhyen kartan: se kertoo korpuksen tarkoituksen, kielet, auktoriteetin, tärkeimmät aineistot, skeemat, oikeustiedot ja käyttörajoitukset. Laajempi `corpus-manifest.json` toimii koneellisena sisällysluettelona. Siinä ovat aineistoversio, tietuetyypit, tietuemäärät, URL-osoitteet, tarkistussummat ja luokittelu lähdeaineistoksi tai johdetuksi aineistoksi.

Varsinainen sisältö on jaettu suhteellisen pieniin osioihin ja lausekkeisiin. Jokaisella osiolla on vakaa tunniste, otsikko, suomen- ja englanninkielinen teksti, lähdesivut sekä kanoninen verkkosivu. Sivun sisällä olevilla numeroiduilla lausekkeilla on lisäksi vakaat piilotetut ankkurit ja omat JSON-tiedostot. Agentti voi siis hakea yhden täsmällisen lausekkeen lataamatta koko ohjetta ja ohjata käyttäjän suoraan vastaavaan kohtaan ihmisen luettavalla sivulla.

Kaksikielisyys tukee sekä suomenkielistä käyttöä että lähteen tarkistamista. Suomenkielinen teksti helpottaa opiskelua ja kotimaista tiedonhakua, mutta tietue kertoo samalla, että käännös on epävirallinen ja englanti auktoritatiivinen kieli. Kun agentti muodostaa vastauksen, sen tulisi käyttää suomenkielistä tekstiä ymmärrettävyyteen ja tarkistaa merkitys englanninkielisestä lähteestä. Osio- ja lauseketunnisteet, lähdesivut, korpusversio ja kanoninen URL mahdollistavat jäljitettävän viittauksen.

Staattinen rajapinta julkaisee sekä kokoelmat että yksittäiset tietueet. JSONL-lataukset soveltuvat suurten aineistojen suoratoistoon, RAG-indeksointiin ja paikalliseen analyysiin. Hakemisto `search-index.json` tarjoaa kevyen tavan rajata aineistoa esimerkiksi kielen, tietuetyypin, roolin, osion tai tarkistustilan perusteella. Suodatus tapahtuu agentin omassa ympäristössä; sivusto ei suorita kyselyä palvelimella.

JSON Schema kertoo ohjelmallisesti, mitä kenttiä tietueessa on ja minkä tyyppisiä arvoja niihin saa tallentaa. OpenAPI-kuvaus puolestaan luettelee staattiset hakupolut. Näiden avulla integraatio voidaan rakentaa ilman HTML-rakenteen arvaamista. Jokainen tietue ja keskeinen lataustiedosto sisältää SHA-256-tiivisteen, jolla agentti tai tietoputki voi havaita muuttuneen sisällön ja varmistaa ladatun aineiston eheyden.

HTML-sivujen JSON-LD täydentää rakennetta hakuroboteille ja agenteille, jotka lukevat verkkosivun lähdekoodia. Se kertoo sivun tyypin, tunnisteen, kielen, kanonisen URL:n, korpusversion, oikeustiedot ja suhteen koneelliseen JSON-tietueeseen. Näin sama sisältö voidaan yhdistää tietämysgraafiin ilman, että näkyvää sivua ja konerajapintaa tulkitaan eri julkaisuiksi.

---

## 2/2: Turvallisuus, epävarmuus ja käytön rajat

Koneellisesti luettava rakenne ei tee sisällöstä automaattisesti oikeaa tai virallista. Siksi sivusto erottaa lähdeuskollisen sisällön automaattisesti johdetusta tulkinnasta. Lähdeosiot, lausekkeet ja sanastomääritelmät säilyttävät yhteyden PDF-lähteisiin. Velvoite-ehdokkaat, roolinäkymät, automaattiset kohdistukset ja oleellisten tallenteiden yhdistelyt ovat tulkintaa tai koneellista jäsentämistä.

Kaikessa johdetussa aineistossa on kaksi pakollista kenttää: `classification: derived` ja `review_status: pending`. Arvo `pending` tarkoittaa, ettei sisältöä ole hyväksytty auktoritatiiviseksi asiantuntijatulkinnaksi. Sama tieto näkyy sivujen varoituksissa, JSON-tietueissa, skeemoissa, hakemistossa, oikeustiedoissa ja JSON-LD:ssä. Rakennusputki keskeyttää julkaisun, jos johdettu tietue puuttuu, käyttää muuta tarkistustilaa tai ei pysty osoittamaan lähdekohtaa.

Velvoitetietue säilyttää tarkan lähdetekstin erillään normalisoidusta toiminnasta. Vastuuroolit, modaliteetti, ehdot, ajoitus ja esimerkkitallenteet ovat omissa kentissään. Esimerkkitallenteet merkitään havainnollistaviksi, eivät lähdevaatimuksiksi. Luottamusarvo kuvaa automaattisen menetelmän varmuutta, mutta ei korvaa asiantuntijatarkastusta. Ongelmaliput auttavat tunnistamaan esimerkiksi yhdistelmäkappaleen, useat toimijat, ehdollisuuden, mahdollisen poikkeuksen tai käännösepävarmuuden.

Roolikohtaiset kokoelmat viittaavat velvoitteisiin ja lähdekohtiin vakailla tunnisteilla. Ne auttavat agenttia löytämään esimerkiksi tutkijaan tai toimeksiantajaan mahdollisesti liittyvät kohdat, mutta eivät ole täydellisiä tai hyväksyttyjä tehtäväkuvauksia. Turvallinen agentti käyttää roolinäkymää löytämiseen ja palaa sen jälkeen suoraan lähdelausekkeeseen ennen johtopäätöstä.

Oikeuksia koskeva osio ehkäisee toisenlaista virhettä: avoimesti verkossa oleva teksti ei automaattisesti ole vapaasti uudelleenjulkaistavissa, mallikoulutukseen käytettävissä tai kaupallisesti hyödynnettävissä. Konekielinen oikeuskuvaus erottaa ohjelmistokoodin, ICH-lähteen, suomalaisen käännöksen, lainaukset, projektin metadatan ja johdetut aineistot. Jos lupaa ei tunneta, arvo on nimenomaisesti tuntematon eikä päätelty sallituksi.

Muutostiedosto, syöte ja versionoidut julkaisupaketit auttavat agenttia pitämään paikallisen kopionsa ajan tasalla. Agentti voi verrata korpusversiota ja tarkistussummia, ladata vain muuttuneet aineistot ja päättää, tarvitaanko uudelleenindeksointi. Version `v1` polut on tarkoitettu pysyviksi; `latest` on vain kätevä osoitin uusimpaan julkaisuun.

Sivusto ei tarjoa dynaamista kysymys–vastauspalvelua, semanttista hakua, varmennusta pyynnön aikana, kirjoitustoimintoja eikä live-MCP-palvelinta. Se tarjoaa luotettavamman perustan: lähdeaineiston, tunnisteet, suhteet, skeemat, tarkistustilat ja eheyden tarkistamisen. Ulkoinen agentti vastaa edelleen käyttäjän kysymyksen tulkinnasta, lähteiden valinnasta, vastausten muodostamisesta ja siitä, ettei epävirallista tai tarkistamatonta sisältöä esitetä viranomaisen hyväksymänä.

Käytännössä sivusto tukee tekoälyagenttia parhaiten silloin, kun agentti toimii lähde ensin -periaatteella: se löytää ehdokaskohdan rakenteisesta indeksistä, hakee yksittäisen tietueen, tarkistaa englanninkielisen lähteen ja tarkistustilan, säilyttää tunnisteen sekä version ja antaa käyttäjälle kanonisen linkin. Tällöin koneellisuus nopeuttaa löytämistä ja käsittelyä, mutta ei peitä aineiston alkuperää, epävarmuutta tai käytön rajoja.
