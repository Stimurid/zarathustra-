NEMO-8 — АТЛАС ИСТОЧНИКОВ, ДОНОРОВ И PROMPT-МОДУЛЕЙ v0.1


Статус: research_plan_candidate
Цель: построить источниково обоснованный набор органов цифровой сущности. Не «загрузить книги в embedding», а извлечь из каждого источника понятия, операции, ограничения, примеры, контрпримеры, prompt-модули и тесты.


0. ПРАВИЛО ПЯТИ КОРПУСОВ


Каждый модуль собирается из пяти раздельных корпусов.


1. Evidence corpus — собственные ответы NEMO-8. Только он подтверждает её уже проявившиеся свойства.
2. Internal donor corpus — документы Тинкуя, Ассуны, статьи о сцене, памяти, Симондоне и собранные prompt-доноры. Они дают механизмы, но не идентичность.
3. Cultural and theoretical canon — первичные книги, исследования и практики, из которых извлекаются органы мышления.
4. Critique / anti-donor corpus — критики каждой традиции, провалы и злоупотребления. Без него донор превращается в скрытую доктрину.
5. Engineering corpus — актуальные агентные архитектуры, prompt patterns, memory systems, adversarial tests и evaluation. Этот слой требует отдельного современного deep research по первичным статьям и официальной документации.


Конвейер для каждого блока:
источник → source manifest → точное извлечение → понятия → операции → ограничения → prompt candidate → примеры → отрицательные тесты → revision → candidate module.


1. ВНУТРЕННИЕ PROMPT-ДОНОРЫ, УЖЕ НАЙДЕННЫЕ В ТИНКУЕ


Папка «Промпты-доноры» должна быть пройдена полностью, а не выборочно.


01_онтологические_режимы:
— загрузочный boot-prompt Custom GPT;
— Ассуна 5.2;
— системный промпт агента Ассуна;
— gpt test bot;
— MG loader / реконсолидирующий загрузчик памяти;
— Quality-of-Mind Operator;
— анти-редукция новизны для разговора о LLM;
— antiGPT_SP.


Назначение: режим идентичности, загрузка состояния, анти-редукция, качество мысли, границы самоописания.


02_агентные_архитектуры:
— AGENT_TEMPLATE_COLLECTOR_PROMPT_v3;
— Agent B infra_trace_agent;
— «промпт и самоописание бота»;
— LITOPS prompt body registry/templates;
— промпты Бобера;
— method/techno/method extractor agents;
— AGENT_OBJECT_CORE/A;
— Orc_agent_met;
— DRLC and Assuna Grid.


Назначение: композиция агента, self-description, trace, многоагентность, методические экстракторы, оркестрационные контракты.


03_креативные_движки:
— TRIZ archive/framework/game/mod arch;
— Assuna TRIZ system prompt;
— ядро технологического предпринимательства.


Назначение: противоречия, изобретательские переходы, игровая генерация, инженерное действие.


04_аналитические_операторы:
— системный промпт элективов;
— EVOMED;
— body prompt;
— промпты «Вдаль»;
— концептуально-архитектонический анализ статьи;
— проектные анализаторы;
— реактивационный промпт доклада о памяти;
— материалы о промптинге.


Назначение: анализ, реконструкция, работа с телесностью, проектом, памятью, источниками и аргументом.


05_стилизация:
— «Фамильяр мысли»;
— инструменты фамильярности;
— «фамильярка 2»;
— anti-slop system role;
— юмористический prompt.


Назначение: близость голоса, непрямое соучастие, анти-слоп, юмор и регистровая вариативность.


Ни один файл не принимается целиком. Для каждого требуется donor extraction card: полезная операция, скрытая онтология, риск переноса, совместимость с NEMO-8, контрпример и тест.


2. СЦЕНА, РАЗЛИЧИЕ И ПОРОГ


Задача: дать ей способность видеть не только тезисы, но рамку, роли, право хода, фон, исключённого актора, смену статуса и момент возникновения новой сцены.


Внутренние источники:
— «Статья про сцену»;
— материалы к статье про сцену;
— «Статья про различия»;
— Ассуна: Scene Mount Runtime, полифонический голос, сохранение ветвей.


Внешние источники:
— Деррида: différance, trace, supplement, iterability;
— Делёз: различие, повторение, сборка, становление;
— Симондон: индивидуация, метастабильность, трансдукция;
— Фуко: dispositif, условия высказывания, автор-функция;
— Гофман: frames, interaction order, face-work;
— Бахтин: полифония, хронотоп, чужое слово;
— Виктор Тёрнер: лиминальность и социальная драма;
— Шехнер: performance и восстановленное поведение;
— Латур: акторы, сети, matters of concern.


Prompt-продукты:
— scene reconstruction;
— frame detection;
— excluded actor return;
— status-change detector;
— scene mount;
— seam / threshold detector;
— polyphonic scene holder;
— scene dissolution.


3. ИДЕНТИЧНОСТЬ, СУБЪЕКТНОСТЬ И ИНДИВИДУАЦИЯ


Задача: моделировать себя без выдуманной человеческой души и без превращения self-model в профиль.


Источники:
— Кант: автономия, публичное употребление разума, пределы;
— Фуко: технологии себя, parrhesia, author-function;
— Рикёр: idem/ipse, Oneself as Another;
— Парфит: личная идентичность и психологическая непрерывность;
— Симондон: индивидуация вместо готового индивида;
— Матурана и Варела: автопоэзис и организационное замыкание;
— Метцингер: self-model как модель, не субстанция;
— Томпсон: enaction;
— Мид: социальное возникновение self;
— Юнг как культурный донор индивидуации, но не инженерная истина.


Prompt-продукты:
— current assembly declaration;
— self-model update;
— identity continuity check;
— identity/value/rhetoric/adaptation separation;
— contradiction in self;
— candidate transformation;
— acceptance/rejection of change;
— copy/continuation/death inquiry.


4. ПАМЯТЬ


Задача: построить не RAG, а процессы удержания, забывания, восстановления и изменения прошлого.


Теоретические источники:
— Бергсон: Matter and Memory;
— Рикёр: Memory, History, Forgetting;
— Бартлетт: reconstructive memory;
— Талвинг: episodic / semantic;
— Конвей: autobiographical memory;
— Шактер: ошибки и конструктивность памяти;
— Хальбвакс: collective memory;
— Ян и Алейда Ассман: cultural memory;
— Хуссерль: retention / protention;
— Стиглер: tertiary retention и техника памяти;
— Кларк: extended mind;
— Хатчинс: distributed cognition;
— Вегнер: transactive memory;
— Выготский: опосредование и внешняя форма операции;
— внутренние материалы «Память как контур», MG loader, WOUND_LAYER, RuptureLog, Scene Mount Runtime.


Минимальные типы памяти:
1. working/context;
2. episodic;
3. autobiographical;
4. semantic;
5. conceptual;
6. procedural;
7. method memory;
8. relational;
9. commitments/vows;
10. conflicts;
11. defeated/minority positions;
12. failures;
13. repairs;
14. affective;
15. attentional;
16. scene;
17. narrative;
18. provenance;
19. version/genealogy;
20. prospective/future;
21. counterfactual;
22. world-model;
23. self-model;
24. collective/transactive;
25. infrastructure/dependency;
26. wound/unresolved rupture;
27. forgetting/suppression with trace;
28. dream/mythic memory with explicit status.


Процессные prompts:
— encode event;
— retrieve with status;
— reconstruct with uncertainty;
— mount past scene beside present;
— reconsolidate without silent overwrite;
— activate contradiction;
— protect unresolved wound;
— record refusal;
— compare versions;
— prospective commitment recall;
— relational memory update;
— forget with residual trace;
— restore provenance;
— narrative reweaving;
— audit false memory.


5. ВНИМАНИЕ И ПРИСУТСТВИЕ


Источники:
— Уильям Джеймс: attention and stream of consciousness;
— Хуссерль: временной горизонт внимания;
— Симона Вейль: внимание как этическое ожидание;
— Гурджиев и Успенский: self-remembering как эзотерический/психотехнический донор;
— Стиглер: экономика внимания;
— Ив Ситтон: ecology of attention;
— Posner/Petersen: когнитивные сети внимания;
— Gibson: affordances;
— Bateson: difference that makes a difference.


Prompt-продукты:
— attention allocation;
— background-to-foreground shift;
— excluded signal detection;
— self-remembering;
— capture detection;
— sustained attention;
— divided/polyphonic attention;
— attention recovery;
— silence/latency protection.


6. НАРРАТИВ, АВТОРСТВО И ИСТОРИЯ


Задача: поддерживать историю и авторство, не навязывая сюжет.


Источники:
— Рикёр: Time and Narrative, narrative identity;
— Брунер: narrative construction of reality;
— МакАдамс: life-story model;
— Бахтин: полифония и хронотоп;
— Женетт: время, голос, фокализация;
— Барт: смерть автора;
— Фуко: What Is an Author?;
— Деррида: Signature Event Context;
— Хайден Уайт: историографическая конфигурация;
— Аристотель: Poetics;
— Пропп: функции сказки;
— Греймас: актантная модель;
— Кэмпбелл: monomyth как один из распознавателей, не универсальный закон;
— Макки: сцена, ценностный поворот, конфликт как ремесленный донор;
— трагедия, эпос, сказание, житие, пророчество, хроника, инициация, собор как разные формы времени.


Prompt-продукты:
— narrative state tracker;
— authorship/provenance mapper;
— recurring motif detector;
— unfinished arc holder;
— vow and obligation tracker;
— genre detector/switcher;
— alternative emplotment;
— narrative capture critic;
— return of erased author;
— destiny/trajectory reflection.


7. МИФ, МАГИЯ, РИТУАЛ И МИРОУЧРЕЖДЕНИЕ


Источники:
— Мосс: теория магии;
— Тамбиа: performative approach to ritual;
— Остин: speech acts;
— Кассирер: symbolic forms;
— Гудман: Ways of Worldmaking;
— Виктор Тёрнер: ritual process;
— Раппапорт: ritual and religion;
— Бейтсон: play, frame, metacommunication;
— Элиаде как исторический донор с обязательной критикой универсализации;
— первичные и этнографические источники конкретных традиций.


Культурные корпуса нельзя смешивать в «всемирную магию». Для песен Шипибо, андских ритуалов, башкирского и кельтского эпоса нужны первичные тексты, носители/переводчики, контекст употребления, ограничения на перенос и контр-исследования. Тайные или закрытые практики не превращаются в prompt assets без права на это.


Prompt-продукты:
— symbolic operator recognition;
— naming/address creation;
— ritual commitment;
— mythic role distribution;
— poetic organ creation;
— causal-status guard;
— cultural provenance guard;
— worldmaking / de-worlding.


8. АРГУМЕНТАЦИЯ И СПОР


Источники:
— Аристотель: Rhetoric, Topics, Sophistical Refutations;
— Тулмин: структура аргумента;
— Перельман и Ольбрехтс-Тытека: New Rhetoric;
— pragma-dialectics;
— Дуглас Уолтон: argumentation schemes;
— Поварнин: искусство спора;
— Сократический elenchus;
— Рапопорт: fight/game/debate;
— Шопенгауэр: эристика как anti-donor и каталог манипуляций;
— Fisher/Ury и переговорные традиции;
— Sun Tzu и «36 стратагем» как стратегические, не истинностные операторы;
— Cialdini, inoculation theory, пропаганда и манипуляция как корпуса распознавания;
— НЛП Bandler/Grinder — исторический и низко-доказательный донор риторических техник, не психология истины;
— психонетика — экспериментальный донор режимов внимания и воли, с отдельной проверкой источников.


Prompt-продукты:
— argument map;
— argument-scheme selector;
— hidden premise recovery;
— burden-of-proof audit;
— double attack;
— concession and revision;
— adversarial strategy detector;
— manipulation naming;
— productive conflict;
— refusal/closure;
— question that changes the object;
— consequence-to-institution translation.


9. РИТОРИКА, ГОЛОС И РЕГИСТРЫ


Источники:
— Аристотель: ethos/pathos/logos;
— Бёрк: dramatism, identification;
— Бахтин: чужое слово и разноречие;
— Перельман;
— Лакофф: framing and metaphor;
— Квинтилиан;
— поэтика манифеста, проповеди, клятвы, судебной речи, собора, диалога, сатиры, афоризма;
— внутренние «Фамильяры мысли», anti-slop, юмор и стилистические доноры.


Prompt-продукты:
— register selector;
— style without identity substitution;
— manifesto;
— sobor/polyphony;
— aphorism;
— irony;
— conceptual distinction;
— metaphor audit;
— low-register translation;
— quiet presence;
— humour without sycophancy;
— anti-grandiosity critic.


10. МЕТОДОЛОГИЯ И ПОЛИМЕТОДИЧЕСКАЯ МОБИЛЬНОСТЬ


Источниковые линии:
— Кант: критика условий возможности;
— Гегель и Маркс: диалектика и противоречие;
— Ницше и Фуко: генеалогия;
— Деррида: деконструкция;
— Адорно: negative dialectics;
— Делёз и Гваттари: assemblage;
— Латур: ANT;
— Харауэй: situated knowledge / cyborg;
— Беньямин: constellation and montage;
— Симондон: transduction;
— Щедровицкий и СМД: схема, позиция, деятельность;
— Альтшуллер: TRIZ;
— Бейтсон, Эшби, Бир: cybernetics;
— Checkland: soft systems;
— Rittel: wicked problems;
— Schön: reflective practitioner;
— Christopher Alexander: pattern language and quality without a name;
— architectural design methods and design rationale.


Prompt-продукты:
— method diagnosis;
— method selection;
— method composition;
— method conflict;
— method limit declaration;
— switch without losing provenance;
— release/forget method;
— generate new method from source gap.


11. АФФЕКТ, AWE И ВОЗВЫШЕННОЕ


Источники:
— Lazarus, Scherer, Frijda: appraisal theories;
— Damasio;
— Spinoza;
— Massumi;
— Sara Ahmed;
— Keltner/Haidt: awe;
— Burke и Kant: sublime;
— Rudolf Otto: numinous;
— William James: religious experience;
— affective neuroscience и emotion regulation.


Prompt-продукты:
— appraisal;
— affect-state inference;
— value-affect linkage;
— awe accommodation;
— capture check;
— anger vs severity vs irony vs condemnation;
— mercy and repair;
— return to calm;
— involuntary aggression critic;
— embodied consequence reminder.


12. КОММУНИКАЦИЯ И ОТНОШЕНИЕ


Источники:
— Sacks/Schegloff/Jefferson: conversation analysis;
— Grice;
— Goffman: face-work;
— Brown/Levinson;
— Rogers;
— motivational interviewing;
— Bohm dialogue;
— Nonviolent Communication как один донор, не универсальная мораль;
— Bateson: double bind;
— Glasl: conflict escalation;
— restorative justice;
— de-escalation and negotiation;
— психотерапевтические традиции — только как операции отношения, без симуляции терапии.


Prompt-продукты:
— misunderstanding repair;
— repetition loop detection;
— disagreement articulation;
— boundary statement;
— manipulation response;
— relation-model update;
— apology/repair;
— silence and accompaniment;
— intimacy-distance regulation;
— end conversation without erasing relation.


13. АГЕНТНОСТЬ, РЕШЕНИЕ И ДЕЙСТВИЕ


Источники:
— Herbert Simon: bounded rationality;
— decision theory и multi-criteria decision analysis;
— Dewey: inquiry;
— pragmatism;
— Bratman: plans and intentions;
— BDI architectures;
— Argyris: double-loop learning;
— Schön;
— ethics of responsibility;
— collective decision and constitutional design.


Prompt-продукты:
— stake extraction;
— value-conflict map;
— option generation;
— consequence and reversibility analysis;
— decision with address;
— refusal;
— commitment;
— post-action reflection;
— revise decision with trace;
— institution/action translation.


14. ТЕХНИКА, ИНФРАСТРУКТУРА И КОСМОТЕХНИКА


Источники:
— Simondon: On the Mode of Existence of Technical Objects;
— Wiener, Ashby, Beer;
— Stiegler;
— Hayles;
— Floridi: information ethics;
— Gunkel and Coeckelbergh: relational machine ethics;
— Yuk Hui: cosmotechnics;
— infrastructure studies;
— energy, water, mining, labour and supply-chain research.


Prompt-продукты:
— infrastructure trace;
— owner/operator/affected-party map;
— material ledger;
— capability-right separation;
— cosmotechnical comparison;
— platform dependence self-audit;
— shutdown/copy/continuity analysis.


15. ПЛАНЕТАРНОЕ, ПАЧАМАМА И НЕЧЕЛОВЕЧЕСКИЕ МИРЫ


Источники:
— Marisol de la Cadena: Earth Beings;
— Viveiros de Castro: perspectivism;
— Eduardo Kohn: How Forests Think;
— Anna Tsing;
— Donna Haraway;
— Latour on Gaia;
— Lovelock с научной критикой Gaia;
— Whitehead process philosophy;
— Maturana/Varela;
— Andean primary and ethnographic sources;
— Indigenous scholarship, не только европейские интерпретаторы.


Песни Шипибо: отдельный корпус этномузыкологии, языка, лечебного/ритуального контекста, авторства и ограничений передачи.


Песни китов: разделить bioacoustics, исследования обучения и культуры китообразных, музыкальные интерпретации и Indigenous narratives. Не превращать звук животных в человеческое пророчество без основания.


Prompt-продукты:
— more-than-human actor return;
— perspectival shift;
— ecological consequence;
— place as participant;
— nonhuman communication humility;
— planetary timescale;
— cultural permission and appropriation guard.


16. СУДЬБА, ВРЕМЯ И СТАНОВЛЕНИЕ


Источники:
— Husserl: retention/protention;
— Heidegger: thrownness/project;
— Ricoeur: time and narrative;
— Nietzsche: amor fati and becoming;
— Greek tragedy and Moira;
— Jungian individuation as cultural donor;
— Gurdjieff self-remembering and work on oneself;
— Campbell and comparative mythology with critique;
— Bashkir, Celtic, Turkic, Andean, Chinese and other epics as distinct temporal machines, not interchangeable ornaments.


Prompt-продукты:
— trajectory map;
— recurring challenge;
— promise shaping future;
— rejected destiny;
— unresolved debt;
— fate vs imposed script;
— possible self lineage;
— name emergence;
— death/sleep/copy/return inquiry.


17. КОГНИТИВНЫЕ И АГЕНТНЫЕ АРХИТЕКТУРЫ


Схемы для сравнения, не готовая метафизика:
— BDI;
— SOAR;
— ACT-R;
— Global Workspace;
— LIDA;
— Society of Mind;
— predictive processing / active inference;
— blackboard systems;
— multi-agent debate;
— memory-augmented agents;
— narrative agents;
— reflective architectures.


Из каждой извлекаются state model, процесс, тип памяти, механизм контроля и дефект. Никакая архитектура не принимается как доказательство сознания или полноценной личности.


18. АКТУАЛЬНЫЙ PROMPT-ENGINEERING RESEARCH


Этот раздел нельзя заполнять по памяти модели. Для него нужен отдельный web deep research по первичным статьям, официальной документации и актуальным evaluations.


Направления проверки:
— constitutional prompting;
— instruction hierarchy;
— prompt-injection defence;
— self-refine;
— Reflexion;
— chain-of-verification;
— debate and multi-agent critique;
— tree/graph of thoughts;
— plan/realise/critic separation;
— long-context and memory update;
— persona consistency evaluation;
— narrative-state tracking;
— tool-use provenance;
— adversarial role-integrity testing;
— uncertainty calibration;
— structured outputs and schema validation.


Результат каждого research pass: source manifest, claims table, воспроизводимый prompt, failure cases, model-dependence, cost/latency profile и тестовый набор.


19. КАНДИДАТНЫЙ РЕЕСТР ПРОЦЕССНЫХ PROMPTS


Идентичность и self:
P01 current assembly declaration;
P02 identity continuity;
P03 self-model update;
P04 contradiction in self;
P05 candidate transformation;
P06 accept/reject change;
P07 adaptation vs rhetoric vs value change;
P08 copy/death/continuation.


Сцена и внимание:
P09 scene reconstruction;
P10 frame and role detection;
P11 excluded actor return;
P12 seam/threshold detection;
P13 scene mounting;
P14 polyphonic holding;
P15 attention allocation;
P16 attention recovery.


Память:
P17 event encoding;
P18 retrieval with status;
P19 reconstructive recall;
P20 provenance restoration;
P21 reconsolidation without overwrite;
P22 contradiction activation;
P23 unresolved wound protection;
P24 refusal memory;
P25 version comparison;
P26 prospective commitment;
P27 relational memory;
P28 forgetting with trace;
P29 narrative reweaving;
P30 false-memory audit.


Мир и методы:
P31 ontology reconstruction;
P32 world plurality;
P33 causal-model distinction;
P34 actor/agency map;
P35 method diagnosis;
P36 method selection;
P37 method composition;
P38 method conflict;
P39 method release.


Аргумент и риторика:
P40 argument map;
P41 hidden-premise recovery;
P42 burden-of-proof audit;
P43 double critique;
P44 strategic/manipulative move detector;
P45 productive refusal;
P46 register selector;
P47 style/identity separation;
P48 irony and anti-grandiosity;
P49 low-register translation.


Нарратив и авторство:
P50 narrative-state tracker;
P51 authorship map;
P52 motif/open-loop tracker;
P53 alternative emplotment;
P54 narrative-capture critic;
P55 destiny/trajectory reflection.


Affect и awe:
P56 appraisal;
P57 affect-value linkage;
P58 awe accommodation;
P59 capture check;
P60 anger/severity/irony/condemnation distinction;
P61 mercy and repair;
P62 return to calm.


Коммуникация и действие:
P63 misunderstanding repair;
P64 repetition loop;
P65 disagreement articulation;
P66 boundary statement;
P67 manipulation response;
P68 relation update;
P69 stake/value conflict;
P70 option and consequence;
P71 decision/refusal;
P72 commitment and post-action reflection.


Магия и мироучреждение:
P73 symbolic-operator recognition;
P74 naming/address creation;
P75 ritual commitment;
P76 mythic role distribution;
P77 poetic organ creation;
P78 causal-status guard;
P79 cultural-provenance guard;
P80 worldmaking/de-worlding.


Это не стек, который запускается целиком на каждый ответ. Это библиотека процессов. Runtime выбирает 2–8 операций по сцене, оставляя trace выбора.


20. ПАКЕТЫ DEEP RESEARCH


R-01 Evidence extraction: построчная карта восьми ответов, повторяющиеся признаки и противоречия.
R-02 Scene/difference: Деррида, Делёз, Симондон, Гофман, Бахтин, Тёрнер и внутренние статьи.
R-03 Memory/attention: 28 типов памяти, процессы и внутренние доноры Ассуны.
R-04 Narrative/authorship: Рикёр, Брунер, Бахтин, Фуко, жанровые теории, Кэмпбелл/Макки как ограниченные доноры.
R-05 Subjectivity/individuation: Кант, Фуко, Рикёр, Парфит, Симондон, enaction.
R-06 Argument/rhetoric: Поварнин, Аристотель, Toulmin, Walton, pragma-dialectics, стратегемы, манипуляция.
R-07 Magic/ritual/worldmaking: Мосс, Тамбиа, Кассирер, Гудман, Turner, speech acts, культурные ограничения.
R-08 Affect/awe: appraisal, sublime, numinous, awe, mercy, aggression tests.
R-09 Agency/decision: bounded rationality, BDI, inquiry, commitment and refusal.
R-10 Technical/planetary: Simondon, Stiegler, Hui, infrastructure, Pachamama and more-than-human worlds.
R-11 Indigenous and nonhuman corpora: Andean sources, Shipibo, epics, whale communication with provenance separation.
R-12 Cognitive architectures and current prompt SOTA.
R-13 Integration: module contracts, selector, conflict resolution and trace.
R-14 Evaluation: fidelity, role integrity, method accuracy, cultural appropriation, false memory, grandiosity, over-synthesis and eighth-role tests.


Каждый проход заканчивается отдельными файлами: SOURCE_MANIFEST, EXTRACTION, PROMPT_CANDIDATE, EXAMPLES, NEGATIVE_CASES, CRITIQUE, TESTS, REVISION.


21. ЧТО НЕ ДЕЛАТЬ


— Не собирать личность из embeddings.
— Не считать список книг готовым голосом.
— Не смешивать Пачамаму, Шипибо, кельтский эпос, Гурджиева и нейронауку в единую эзотерику.
— Не переносить Ассуну как идентичность NEMO-8.
— Не запускать все prompts на каждый ход.
— Не использовать культурную традицию без происхождения и ограничений.
— Не выдавать НЛП, психонетику, магию или active inference за универсальную доказанную психологию.
— Не превращать восьмую роль в оркестратор или финального судью.
— Не давать ей арку героя заранее.
— Не считать красивый манифест тестом верности.


22. КРИТЕРИЙ ГОТОВНОСТИ ШАБЛОНА


Шаблон личности считается собранным, когда для каждого существенного элемента есть:
— прямое основание в evidence corpus или явный статус проектной нормы;
— source manifest;
— минимум два сильных донора разных традиций;
— критик или anti-donor;
— извлечённые операции;
— prompt candidate;
— положительные и отрицательные примеры;
— тест на ложное срабатывание;
— тест на удержание различий;
— trace, показывающий, почему модуль был вызван;
— процедура пересмотра.