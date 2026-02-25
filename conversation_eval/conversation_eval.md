# Domain-specifikus Conversation Eval Jelentés

A domain-specifikus conversation eval alapján a rendszer már jól támogatja a legtöbb gasztronómiai use case-et, de még nem elég rugalmas, ha a felhasználó „kilép” a szűken vett receptszövegből.

---

## 1. Kísérleti elrendezés

### Adatok
- **conversations-2.json** – 24 szimulált beszélgetés (4 persona × 6 goal)
- **judge_results-2.json** – LLM-as-judge értékelés persona–goal páronként

### Personák (batch_config alapján)
- budget_student  
- health_conscious_foodie  
- impatient_chef  
- beginner_cook  

### Goalok
- recipe_discovery  
- ingredient_swap  
- step_by_step_guide  
- dietary_filtering  
- recipe_variant_suggestion  
- menu_planning  

### Metrikák (0–3 skála)
- **goal_completion** – mennyire érte el a beszélgetés a kitűzött célt  
- **answer_quality** – mennyire relevánsak, hasznosak és koherensek a válaszok  

### Összesített eredmény
- **Átlagos goal_completion:** 2,21 / 3  
- **Átlagos answer_quality:** 1,79 / 3  

Ez jelentős javulás az előző, általánosabb setup ~1,17 / 1,5-ös átlagához képest.

---

## 2. Mi működik jól?

### 2.1. Budget Student – olcsó, egyszerű receptek

**recipe_discovery**  
- goal_completion: 3  
- answer_quality: 2  
A beszélgetés végére a user egy egyszerű, elkészíthető Pad Thai receptet kap, az alapanyagokhoz és eszközökhöz igazítva.

**recipe_variant_suggestion**  
- goal_completion: 3  
- answer_quality: 3  
A bot részletes, érthető tippeket ad a spagetti vegán / kevésbé zsíros változatához, figyelembe véve a költségkeretet.

**menu_planning**  
- goal_completion: 3  
- answer_quality: 2  
Egy olcsó, egyszerű thai menü áll össze; a válaszok relevánsak és támogatók.

**Megállapítás:**  
A rendszer jól teljesít, amikor:
- egyszerű, olcsó recepteket kell ajánlani,
- klasszikus tésztás / thai recepteket kell variálni,
- menüből több, egymáshoz illeszkedő receptet kell választani.

---

### 2.2. Health Conscious Foodie – domainen belüli recipe discovery

**recipe_discovery**  
- goal_completion: 3  
- answer_quality: 3  

A user egy részletes, egészségtudatos, teljes kiőrlésű tésztás, mogyorós thai tészta receptet kap, a kívánt pikáns ízvilággal.  
A judge szerint a válaszok pontosak, relevánsak, jól strukturáltak.

A RAG + receptkorpusz itt elég információt ad ahhoz, hogy a „health conscious” szempontokat is értelmesen leképezze.

---

## 3. Hol bukik el a rendszer?

### 3.1. Ingredient swap – amikor nincs a korpuszban a tudás

**Legmarkánsabb példa:**  
health_conscious_foodie – ingredient_swap  
- goal_completion: 1  
- answer_quality: 0  

Feladat: mandulatej helyettesítése.  
A bot minden válaszában csak azt ismétli, hogy nem tud segíteni, nem ad alternatívát.  
A user hoz fel ötleteket, a bot nem épít rájuk.

**Ez a „RAG-fal” jelenség:**
- ha a konkrét helyettesítési tipp nincs a markdown kontextusban, a rendszer inkább semmit nem mond,
- nincs engedélyezve, hogy általános konyhai tudást használjon fallbackként.

---

### 3.2. Step-by-step guide – félbehagyott vezetés

Több personánál hasonló minta:

**budget_student – step_by_step_guide**  
- goal_completion: 2  
- answer_quality: 1  
A végén egy egyszerű tojásos tészta lépéseihez eljutnak, de a bot közben összekeveri más recepttel.

**health_conscious_foodie – step_by_step_guide**  
- goal_completion: 1  
- answer_quality: 1  
A bot jól indul, de később nem reagál helyesen a megerősítésekre, és nem jutnak el egy teljes receptig.

**Minta:**  
A rendszer:
- el tud indulni lépésről lépésre,
- de ha közben eltérő kérdések jönnek, könnyen kizökken vagy keveri a recepteket.

---

### 3.3. Health-conscious use case-ek – makró / táplálkozási adatok hiánya

**dietary_filtering** és **recipe_variant_suggestion**  
- goal_completion: 2  
- answer_quality: 1  

A bot:
- ajánl diétásnak tűnő fogást, de nem tud makrókat mondani,
- a user ötleteit nem tudja validálni vagy kibontani.

**Ok:**  
A korpusz nem tartalmaz makrotápanyag-információt → RAG-ből nem nyerhető ki.

---

## 4. Erősségek és gyengeségek (összefoglalva)

### Erősségek
- Magas **goal_completion** átlag (2,21 / 3): a legtöbb beszélgetésben a user eljut egy használható receptig vagy menüig.
- Reális, gasztronómiai personákon jól teljesít (budget_student, health_conscious_foodie).
- Inkább mond „nem tudom”, minthogy kitaláljon rossz helyettesítőt.

### Gyengeségek
- Túl szűk RAG-guardrail: ha nincs kontextus, a bot gyakran semmit nem mond.
- Step-by-step szcenáriókban nem mindig viszi végig a receptet.
- Health-conscious esetekben nem tud táplálkozási adatokat generálni.

---

## 5. Javasolt fejlesztések

### Hibrid tudás engedése a System Promptban
Új szabály:  
„Elsősorban a RAG-ből vett kontextusra támaszkodj, de általános konyhatechnikai kérdésekben használhatod az általános szakácstudásodat is.”

**Várható hatás:**  
Ingredient_swap és step_by_step_guide goaloknál nő a goal_completion és answer_quality.

---

### Jobb fallback viselkedés nincs-találat esetén
Ha nincs makró-információ:
- jelezze ezt őszintén,
- de ajánljon egy „jó közelítést” (pl. teljes kiőrlésű + zöldségdomináns alternatívát).

---

### Intent- és clarifying kérdés-stratégia finomhangolása
recipe_discovery és menu_planning során:
- ne adja fel az első homályos kérdés után,
- tegyen fel 2–3 célzott pontosító kérdést.

---

### Step-by-step guide stabilizálása
Promptban kiemelni:
- „Ha step-by-step módba léptél, maradj a kiválasztott recepten.”  
- „Röviden foglald össze, hol tartunk, mielőtt továbblépsz.”
