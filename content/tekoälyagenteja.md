
---
title: "Sivuston tuki tekoälyagenteille"
id: "ich-e6-r3-ai-agent-support"
content_type: "analysis"
language: "fi"
lang: "fi"
schema_type: "TechArticle"
publish: true
permalink: "/tekoälyagenteja/"
---

## Arvion lähtökohta

Tässä arviossa **agenteilla** tarkoitetaan tekoäly- ja LLM-pohjaisia järjestelmiä, jotka selaavat, hakevat, indeksoivat, siteeraavat tai hyödyntävät verkkosisältöä.

**Kokonaisarvio:** 

Sivusto tukee **hyvin sisältöä lukevia, hakevia ja vastauksia lähteisiin perustavia agentteja**, erityisesti silloin, kun mukaan otetaan sivustoon liittyvä julkinen GitHub-repositorio. Pelkkä julkaistu verkkosivusto on kohtalaisen agenttiystävällinen, mutta repositorio nostaa tuen vahvaksi RAG- ja tietojenkäsittelykäyttöön. Toimintoja suorittavien ja työkaluja kutsuvien agenttien tuki on hyvin vähäinen.

| Agentin käyttötapaus | Tuen taso |
|---|---|
| Selainpohjainen lukeminen ja navigointi | **Hyvä** |
| RAG-indeksointi ja semanttinen haku | **Vahva repositorion kanssa, kohtalainen pelkällä sivustolla** |
| Lähteisiin perustuvat vastaukset ja viittaukset | **Hyvä** |
| Ohjelmallinen kyselyrajapinta | **Heikko** |
| Työkalujen käyttö ja transaktiiviset toiminnot | **Käytännössä puuttuu** |
| Muutosten seuranta ja synkronointi | **Heikko** |

## Sivuston tarjoama agenttituki

### 1. Indeksoitavat ja riittävän pieniin osiin jaetut sisältösivut

Ohjeisto julkaistaan tavallisena, julkisesti saatavana HTML-sisältönä ilman kirjautumis- tai istuntovaatimuksia. Sisältö on jaettu suhteellisen pieniin sivuihin, joilla on vakaalta vaikuttavat URL-polut, otsikot, murupolut, sisäiset linkit, aiheeseen liittyvät käsitteet ja paluulinkit.

Tämä on selaaville ja tietoa hakeville agenteille huomattavasti helpompaa käsitellä kuin yksi suuri PDF-tiedosto tai kokonaan JavaScriptin varassa toimiva sovellus.

Sivut sisältävät myös:

- suomenkielisen sisällön
- vastaavan englanninkielisen lähdetekstin silloin, kun kohdistus on onnistunut
- lähdeosion ja sivunumerot
- linkit sanastokäsitteisiin
- linkit aiheeseen liittyville sivuille

Näiden ominaisuuksien avulla agentti voi hakea rajatun tekstikohdan ja säilyttää käyttökelpoisen alkuperätiedon sen sijaan, että koko aineisto käsiteltäisiin yhtenä jäsentymättömänä tekstimassana.

- Sivusto: <https://mvattulainen.github.io/ichgcpe6r3fin/>
- Esimerkkisivu: <https://mvattulainen.github.io/ichgcpe6r3fin/01-johdanto/johdanto>

### 2. Hyödylliset navigointi- ja löytämistoiminnot

Sivusto tarjoaa:

- sanaston
- englanti–suomi-termihakemiston
- roolikohtaisia näkymiä
- vastuita kuvaavia taulukoita

Quartz-konfiguraatiossa ovat käytössä muun muassa murupolut, paluulinkit, sivustopuu, asiakaspuolen haku, linkkien indeksointi, sisältöindeksi ja sivustokartan muodostaminen. Nämä helpottavat sekä selainagenttien aineiston löytämistä että ihmisen valvomaa hakutulosten tarkastamista.

RSS-syöte on kuitenkin poistettu käytöstä.

- Sanasto: <https://mvattulainen.github.io/ichgcpe6r3fin/sanasto/>
- Quartz-konfiguraatio: <https://github.com/mvattulainen/ichgcpe6r3fin/blob/main/quartz.config.yaml>

### 3. Vahva koneluettava rinnakkaisrepositorio

Merkittävin agenttituki löytyy näkyvän käyttöliittymän sijasta sivustoon liittyvästä julkisesta GitHub-repositoriosta. Se sisältää kanonisia JSON-aineistoja muun muassa seuraavista kohteista:

- dokumentit
- osiot
- suomi–englanti-kohdistukset
- termit ja sanastomerkinnät
- roolit
- velvoitteet
- keskeiset asiakirjat
- poimintatulokset

Repositoriossa on lisäksi generoitu Markdown-sisältö, lähde-PDF:t, lähdemanifestit, validointiohjelmat ja laadunvarmistusraportit.

Tämä muodostaa hyvän pohjan esimerkiksi seuraaville ratkaisuille:

- RAG-indeksi
- tietämysgraafi
- termipalvelu
- toimialakohtainen tekoälyavustaja
- velvoitteiden tai roolien hakupalvelu

Tietueissa käytetään eksplisiittisiä tunnisteita ja melko rikkaita kenttiä. Velvoitetietueet sisältävät esimerkiksi:

- vastuulliset ja tukevat toimijat
- lähdeosiot
- suomen- ja englanninkielisen lähdetekstin
- velvoittavuuden modaliteetin
- normalisoidun toiminnan
- ajoituksen
- luottamusarvon
- todentilan
- tarkastustilan

Myös kohdistustietueissa on tunnisteet, menetelmä, luottamusarvo ja tarkastustila.

- Repositorio: <https://github.com/mvattulainen/ichgcpe6r3fin>
- Velvoiteaineisto: <https://github.com/mvattulainen/ichgcpe6r3fin/raw/refs/heads/main/data/obligations.json>

### 4. Hyvä alkuperä-, eheys- ja auktoriteettitieto

Lähdemanifesti erottaa toisistaan:

- auktoritatiivisen englanninkielisen asiakirjan
- epävirallisen suomenkielisen käännöksen

Manifestissa ilmoitetaan lisäksi kanoniset lähdesijainnit ja SHA-256-tarkistussummat. Repositorion sisäisten raporttien mukaan lähde-PDF:ien tarkistussummat täsmäävät ja poimittujen osioiden sekä sanastosisällön vastaavuus lähdeaineistoon on tarkistettu.

Tämä on arvokasta agenteille, joiden täytyy:

- tunnistaa auktoritatiivinen kieliversio
- erottaa lähdeaineisto johdetusta tiedosta
- havaita tahattomat lähdemuutokset
- säilyttää jäljitettävyys vastauksissa

Generoidun Markdownin front matter -metatiedoissa on muun muassa:

- pysyvä tunniste
- sisältötyyppi
- dokumentti- ja osiotunniste
- kieli
- käännöstila
- auktoritatiivinen kieli
- lähdesivut
- aliasnimet
- tunnisteet
- roolit
- tarkastustila
- lähdesuhteet

Tämä on huomattavasti parempi lähtökohta repositoriota hyödyntäville agenteille kuin pelkän renderöidyn HTML:n otsikkorakenteen tulkitseminen.

- Lähdemanifesti: <https://github.com/mvattulainen/ichgcpe6r3fin/blob/main/sources/manifest.yaml>
- Esimerkki Markdown-lähteestä: <https://github.com/mvattulainen/ichgcpe6r3fin/blob/main/content/01-johdanto/johdanto.md>

### 5. Epävarmuus tuodaan näkyviin

Sivusto ilmoittaa selvästi, että roolikohtaiset näkymät ovat:

- automaattisesti generoituja
- kokeellisia
- sisällöllisesti tarkastamattomia

Johdetuissa velvoitetiedoissa on luottamus- ja tarkastustilakentät. Esimerkkitodisteet on merkitty havainnollistaviksi eikä lähdevaatimuksiksi.

Näin huolellisesti toteutettu agentti voi:

- alentaa tarkastamattoman tiedon painoarvoa
- suodattaa johdetut väitteet pois
- erottaa lähdetekstin tulkinnasta
- nostaa epävarmat kohdat ihmisen tarkastettaviksi

Kaksi suomenkielistä rakennetta on lisäksi ilmoitettu englanninkieliseen lähteeseen kohdistamattomiksi sen sijaan, että niille olisi annettu epäluotettava vastaavuus.

- Esimerkkikuvaus tutkijan roolinäkymästä: <https://mvattulainen.github.io/ichgcpe6r3fin/roolipohjaiset-nakymat/tutkija>
- Kohdistamaton rakenne: <https://mvattulainen.github.io/ichgcpe6r3fin/01-johdanto/soveltamisala>

## Agenttituki, jota sivusto ei tarjoa

### 1. Agenttikohtainen aloituspiste puuttuu

Sivustolta tai repositoriosta ei löytynyt dokumentoitua:

- `llms.txt`-tiedostoa
- agenttimanifestia
- mallille tarkoitettua aineisto-opasta
- muuta vastaavaa koneluettavaa aloituspistettä

Agentin täytyy siis löytää sivuston rakenne tavallisen indeksoinnin avulla tai tuntea GitHub-repositorion rakenne ennakolta.

Hyödyllinen agenttikohtainen aloituspiste voisi kuvata ainakin:

- auktoritatiiviset ja käännetyt lähteet
- kanoniset rakenteiset aineistot
- käyttö- ja lisenssiehdot
- tarkastetun ja automaattisesti johdetun tiedon erot
- suositellun viittaustavan
- aineiston version
- viimeisimmän päivityspäivän

### 2. Tuettu ohjelmallinen kyselyrajapinta puuttuu

Sivustolla ei ole dokumentoitua:

- REST-rajapintaa
- GraphQL-rajapintaa
- OpenAPI-kuvausta
- MCP-palvelinta

JSON-tiedostot ovat erittäin hyödyllisiä, mutta ne ovat repositorioartefakteja eivätkä muodollisesti tuettu kyselypalvelu.

Agentti ei voi suoraan ja luotettavasti kutsua esimerkiksi seuraavia toimintoja:

```text
get_section(section_id)
search_guideline(query, language)
get_term(term_id)
list_obligations(actor, review_status)
get_alignment(finnish_section)
````

Sivuston asiakaspuolen haku auttaa ihmiskäyttäjää, mutta se ei muodosta vakaata koneiden välistä sopimusta. Siitä puuttuvat dokumentoidut:

- kyselyparametrit
- tietomallit
- sivutus
- virhetilanteet
- yhteensopivuus- ja versiolupaukset

### 3. Rakenteisen tiedon löydettävyys suoraan verkkosivustolta on rajallinen

Etusivu linkittää GitHub-repositorioon, mutta julkaistu sivusto ei nosta JSON-aineistoja selvästi esiin ensisijaisina koneluettavina esitysmuotoina.

Pelkästään verkkosivustolla toimiva agentti saattaa tämän vuoksi:

- indeksoida vain HTML:n
- jättää kanoniset JSON-rakenteet löytämättä
- tulkita johdetun sisällön lähdesisällöksi
- menettää tietueiden tunnisteita ja tarkastustiloja

Lähdeaineistossa ja front matter -metatiedoissa esiintyy Schema.org-tyyppejä, kuten `TechArticle` ja `DefinedTerm`, mutta ei ole varmistettu, että ne julkaistaan tuotantosivuilla standardinmukaisena JSON-LD:nä.

Front matter auttaa repositoriota lukevaa agenttia, mutta voi jäädä tavalliselta verkkohakurobotilta kokonaan näkymättömäksi.

### 4. Toimintoja suorittavien agenttien tuki puuttuu

Kyseessä on staattinen tietoresurssi. Sivusto ei tarjoa dokumentoituja toimintoja esimerkiksi seuraaviin tehtäviin:

- tietojen lähettäminen
- työnkulun käynnistäminen
- tutkimussuunnitelman validointi
- vaatimustenmukaisuuspäätöksen kirjaaminen
- kliinisen tutkimuksen ulkoisten järjestelmien käyttäminen
- tehtävien tai hyväksyntöjen hallinta

Tämä ei välttämättä ole suunnitteluvirhe, koska aineisto on tarkoitettu viiteaineistoksi. Käytännössä toimintoja suorittava agentti voi kuitenkin vain lukea, hakea, navigoida ja muuntaa tietoa ulkoisissa järjestelmissä. Se ei voi toteuttaa toimialan toimenpiteitä sivuston kautta.

### 5. Muutosten synkronointi ja seuranta on heikkoa

Vaikka sivustokartan luonti on käytössä:

- RSS on poistettu käytöstä
- repositoriossa ei ole selkeää muodollista julkaisukäytäntöä
- dokumentoitua muutosvirtaa ei ole
- webhookeja ei ole
- versioitua rajapintaa ei ole
- aineistojulkaisujen arkistoa ei ole
- migraatiopolitiikkaa ei ole

Integroivan agentin olisi todennäköisesti seurattava GitHub-commit-muutoksia ja pääteltävä itse, vaikuttaako muutos:

- lähdetekstiin
- generoituun sivuun
- johdettuun tulkintaan
- tietomalliin
- tarkastustilaan

### 6. Sisällön uudelleenkäyttöoikeudet eivät ole riittävän yksiselitteisiä

Repositoriossa oleva MIT-lisenssi liittyy Quartz-ohjelmistoon, mutta se ei yksiselitteisesti määritä käyttöoikeuksia:

- ICH:n alkuperäiselle lähdeaineistolle
- suomenkieliselle käännökselle
- johdetuille tietomalleille ja aineistoille

Etusivulla on riippumattomuutta ja auktoriteettia koskeva vastuuvapauslauseke, mutta selkeää koneluettavaa sisältölisenssiä tai tekoäly- ja indeksointikäyttöä koskevaa politiikkaa ei ole näkyvästi esitetty.

Tämä on olennainen puute agenteille ja niitä rakentaville organisaatioille, jos tarkoituksena on:

- julkaista tekstikatkelmia uudelleen
- muodostaa omia aineistoja
- kouluttaa tai hienosäätää malleja
- rakentaa kaupallinen hakupalvelu
- säilyttää aineistoa pitkäaikaisesti
- Lisenssitiedosto: [https://github.com/mvattulainen/ichgcpe6r3fin/blob/main/LICENSE.txt](https://github.com/mvattulainen/ichgcpe6r3fin/blob/main/LICENSE.txt)

### 7. Johdettu tieto ei ole vielä riittävän auktoritatiivista autonomiseen käyttöön

Normalisoidut rooli- ja velvoitenäkymät odottavat edelleen asiantuntijatarkastusta. Osa velvoitetietueista perustuu yhdistelmäkappaleisiin, joissa voi olla:

- useita toimijoita
- ehtoja
- poikkeuksia
- kontekstisidonnaisia ilmaisuja
- useita samanaikaisia velvoitteita

Agentti saattaa virheellisesti muuntaa tällaisen kohdan yhdeksi yksinkertaiseksi ja itsenäiseksi vaatimukseksi.

Sivusto varoittaa tästä, mutta ei teknisesti pakota alavirran käyttäjiä suodattamaan tietoa tarkastustilan perusteella.

Johdetut aineistot soveltuvat hyvin seuraaviin käyttötarkoituksiin:

- tiedon löytäminen
- ehdokasväitteiden poiminta
- asiantuntijan avustaminen
- hakua täydentävä aineisto
- tarkastettavien kohtien priorisointi

Niitä ei tule vielä käyttää yksinään autonomisten vaatimustenmukaisuuspäätelmien perustana.

## Käytännön johtopäätös

Projektissa on jo useita **agenttivalmiin tietoaineiston** ominaisuuksia:

- pieniin osiin jaetut sisältösivut
- kaksikieliset lähdekatkelmat
- vakaat tunnisteet
- alkuperätiedot ja jäljitettävyys
- rakenteiset JSON-aineistot
- validointiraportit
- luottamusarvot
- eksplisiittiset tarkastustilat

Suurin rajoite on se, että nämä ominaisuudet muodostavat **hyvin jäsennellyn repositorion**, eivät valmista **agenttirajapintaa**.

Agenttijärjestelmän rakentaja voi luoda aineiston päälle laadukkaan ratkaisun, mutta joutuu toteuttamaan itse:

- aineiston löytämisen
- lataamisen
- indeksoinnin
- kyselyrajapinnan
- versioseurannan
- tarkastustilojen suodatuksen
- lisenssien ja käyttöoikeuksien hallinnan

## Suositellut jatkokehitystoimet

Suurimman hyödyn tuottaisivat seuraavat parannukset:

1. Julkaistaan agentteja varten aineistomanifesti, esimerkiksi `llms.txt` tai vastaava.
2. Tarjotaan versioidut JSON-aineistot ja niiden JSON Schema -kuvaukset.
3. Julkaistaan renderöidyillä sivuilla standardinmukainen JSON-LD.
4. Toteutetaan vain luku -tyyppinen OpenAPI- tai MCP-rajapinta.
5. Otetaan käyttöön muutosvirta, RSS/Atom-syöte tai aineistokohtaiset julkaisut.
6. Määritetään selkeästi lähdetekstin, käännöksen ja johdetun tiedon lisenssit.
7. Asiantuntijatarkastetaan rooli- ja velvoiteaineistot.
8. Dokumentoidaan suositeltu viittaus- ja lähteistyskäytäntö agenteille.
9. Lisätään aineistoversio ja viimeisin päivitysaika kaikkiin koneluettaviin esityksiin.
10. Tarjotaan valmiit suodatusmekanismit tarkastamattoman ja matalan luottamuksen tiedon poissulkemiseen.  
    
