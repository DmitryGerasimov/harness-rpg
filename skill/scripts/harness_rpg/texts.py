"""Game vocabulary, one shape per language, and the helpers that pick a word form or write a number.

Lists may differ in length between the languages: noun forms for a count (three in Russian, two in English)
and word lists.
"""

from .constants import (
    ACTIVE_GAP_CAP_SECONDS, CHA_ACTIONS_MID, CON_COMPACTIONS_MID, CON_HOURS_MID, CON_STREAK_MID, DEX_SUCCESS_LO,
    INT_BREADTH_MID, INT_DOCS_MID, NIGHT_END_HOUR, SCHOOLS, STR_EDITS_MID, WIS_AUTONOMY_MID, WIS_FRICTION_HI,
    WIS_PLAN_SHARE_MID,
)


TEXTS = {
    'ru': {
        'ranks': ('Новичок', 'Ученик', 'Подмастерье', 'Умелец', 'Эксперт', 'Мастер', 'Грандмастер'),
        'rarities': {
            'common': 'обычная', 'uncommon': 'необычная', 'rare': 'редкая', 'epic': 'эпическая',
            'legendary': 'легендарная',
        },
        # Name, the short line and the long story of each school for the hero-card tooltip.
        'schools': {
            'smith': (
                'Кузнец', 'куёт код: фичи, рефакторинг, тесты',
                'Школа ремесла кода. Сюда идут навыки, которые помогают писать, менять и проверять код: правила '
                'ремесла, тесты и заготовки, ревью, знание устройства модулей. Кузнец силён, когда герой часто '
                'берётся за молот — пишет новое, перековывает старое и закаляет тестами.',
            ),
            'ranger': (
                'Следопыт', 'идёт по следу: расследования, отладка, инциденты',
                'Школа расследований. Сюда идут навыки поиска причин: разбор ошибок и происшествий, чтение следов '
                'в логах и метриках, отладка, знание устройства прода. Следопыт силён, когда герой часто идёт по '
                'следу беды и находит, откуда она пришла.',
            ),
            'engineer': (
                'Инженер', 'строит и запускает: сборка, релизы, деплой, инфраструктура',
                'Школа сборки и запуска. Сюда идут навыки для релизов и выкатки, веток, сборок, установки и '
                'инфраструктуры. Инженер силён, когда герой часто что-то собирает, выкатывает и чинит под нагрузкой.',
            ),
            'alchemist': (
                'Алхимик', 'добывает смысл из данных: запросы, выборки, аналитика',
                'Школа данных. Сюда идут навыки для запросов к базам, выборок, аналитики и графиков. Алхимик силён, '
                'когда герой часто превращает сырые данные в ответы.',
            ),
            'bard': (
                'Бард', 'владеет словом: тексты для людей — документы, статьи, письма, отчёты',
                'Школа слова. Сюда идут навыки, где текст — сам результат для людей: документы и статьи, отчёты, '
                'письма и послания. Записки и поручения, которыми герой ведёт свою свиту, сюда не идут — они у '
                'Призывателя. Бард силён, когда герой много пишет для других и умеет рассказать о сделанном.',
            ),
            'summoner': (
                'Призыватель', 'ведёт свиту: помощники, их поручения и память, обустройство лагеря',
                'Школа свиты. Сюда идут навыки управления помощниками и собственным снаряжением: роли в отряде, '
                'поручения по кругу и по расписанию, записки и память свиты, обустройство лагеря. Призыватель '
                'силён, когда герой ведёт за собой свиту.',
            ),
            'wanderer': (
                'Странник', 'берётся за всё за пределами разработки: быт, хобби, личные дела',
                'Школа всего остального. Сюда идут навыки за пределами разработки: быт, хобби, финансы, '
                'путешествия, личные дела. Странник силён, когда герой помогает и вне работы.',
            ),
        },
        'no_school': ('Без школы', 'навыки, которым ещё не выбрана школа'),
        # Epithet of a pure class, when one school clearly outweighs the rest.
        'epithets': {
            'smith': 'Чистокровный кузнец',
            'ranger': 'Зоркий следопыт',
            'engineer': 'Умнейший инженер',
            'alchemist': 'Мудрейший алхимик',
            'bard': 'Непревзойдённый бард',
            'summoner': 'Властный призыватель',
            'wanderer': 'Вечный странник',
        },
        # Each hybrid and what it turns out to be: shown in the class tooltip.
        'hybrids': {
            frozenset(('smith', 'ranger')): (
                'Охотник на баги', 'выслеживает ошибку и тут же перековывает код, чтобы она не вернулась'),
            frozenset(('smith', 'engineer')): (
                'Механик', 'сам куёт детали и сам собирает из них работающую машину'),
            frozenset(('smith', 'alchemist')): (
                'Артефактор', 'вплавляет данные в код: из чисел выковывает рабочие инструменты'),
            frozenset(('smith', 'bard')): (
                'Рунописец', 'пишет код как текст и текст как код: у каждой строки есть своё слово'),
            frozenset(('smith', 'summoner')): (
                'Мастер големов', 'куёт руками помощников: свита работает молотом, а он направляет удар'),
            frozenset(('smith', 'wanderer')): (
                'Бродячий кузнец', 'носит наковальню с собой: куёт и по работе, и для себя'),
            frozenset(('ranger', 'engineer')): (
                'Страж рубежей', 'держит рубежи: замечает беду в логах и тут же чинит укрепления'),
            frozenset(('ranger', 'alchemist')): (
                'Травник', 'ищет корни бед в данных и лечит их выборками и запросами'),
            frozenset(('ranger', 'bard')): (
                'Летописец', 'расследует и записывает: каждая находка становится летописью'),
            frozenset(('ranger', 'summoner')): (
                'Повелитель зверей', 'пускает по следу свору помощников и собирает всё, что они нашли'),
            frozenset(('ranger', 'wanderer')): (
                'Искатель приключений', 'идёт по следу везде — и в работе, и в жизни'),
            frozenset(('engineer', 'alchemist')): (
                'Техномант', 'строит системы, что живут на данных, и данные, что питают системы'),
            frozenset(('engineer', 'bard')): (
                'Глашатай', 'выпускает релизы и возвещает о них миру: сборка и слово идут рука об руку'),
            frozenset(('engineer', 'summoner')): (
                'Командир', 'руководит стройкой: помощники собирают, выкатывают и докладывают'),
            frozenset(('engineer', 'wanderer')): (
                'Изобретатель', 'чинит и строит всё подряд — от прода до полки на кухне'),
            frozenset(('alchemist', 'bard')): (
                'Звездочёт', 'читает судьбу по числам и пересказывает её понятными словами'),
            frozenset(('alchemist', 'summoner')): (
                'Некромант', 'поднимает ответы из глубин данных руками призванных помощников'),
            frozenset(('alchemist', 'wanderer')): (
                'Знахарь', 'варит зелья из данных — и рабочих, и житейских'),
            frozenset(('bard', 'summoner')): (
                'Чародей', 'заклинает словом: каждое его слово — заклинание, а помощники — его свита'),
            frozenset(('bard', 'wanderer')): (
                'Менестрель', 'странствует со словом: пишет и о работе, и обо всём на свете'),
            frozenset(('summoner', 'wanderer')): (
                'Шаман', 'призывает духов-помощников и для дела, и для быта'),
        },
        'no_class': ('Новобранец', 'навыки ещё не разложены по школам: класс появится, когда их разметят'),
        'skill_fallback': 'Безымянный приём',
        'gear_fallback': 'Безымянный артефакт',
        'slots': {
            'helmet': ('Шлем', 'наблюдаемость: логи, метрики, мониторинг, инфраструктура'),
            'amulet': ('Амулет', 'базы данных и выборки данных'),
            'horn': ('Горн', 'общение: мессенджеры, почта, уведомления'),
            'boots': ('Сапоги', 'браузер и путешествия по вебу'),
            'grimoire': ('Гримуар', 'знания: документация, заметки, базы знаний'),
            'ring': ('Кольцо', 'задачи: трекеры, проекты, планирование'),
            'gloves': ('Перчатки', 'ремесло кода: репозитории, сборки, ревью'),
            'cloak': ('Плащ', 'файлы, документы и облачные хранилища'),
        },
        'bag': 'инвентарь: всё, что не подходит ни к одному слоту',
        'medals': ('бронза', 'серебро', 'золото'),
        # Name, criteria with {n} for the threshold, noun forms for {n}.
        'achievements': {
            'phoenix': ('Феникс', 'пережить {n} памяти за один поход и продолжить путь',
                        ['сжатие', 'сжатия', 'сжатий']),
            'flawless': ('Безупречный', 'пройти поход в {n} без единой ошибки', ['действие', 'действия', 'действий']),
            'warlord': ('Полководец', 'призвать {n} за один поход', ['помощника', 'помощников', 'помощников']),
            'marathon': ('Марафонец', f'проработать {{n}} подряд — без пауз дольше {ACTIVE_GAP_CAP_SECONDS // 60} '
                         'минут', ['час', 'часа', 'часов']),
            'trek': ('Дальний поход', f'провести в работе {{n}} за один поход — паузы дольше '
                     f'{ACTIVE_GAP_CAP_SECONDS // 60} минут не в счёт', ['час', 'часа', 'часов']),
            'tireless': ('Неутомимый', 'работать {n} подряд', ['день', 'дня', 'дней']),
            'versatile': ('Мастер на все руки', 'за один день применить навыки {n}',
                          ['школы', 'разных школ', 'разных школ']),
            'strategist': ('Стратег', 'сначала составить план, а потом действовать, в {n}',
                           ['походе', 'походах', 'походах']),
            'polyglot': ('Полиглот', 'править файлы {n}', ['типа', 'разных типов', 'разных типов']),
            'explorer': ('Странник миров', 'поработать в {n}', ['месте', 'разных местах', 'разных местах']),
            'night_owl': ('Ночная сова', f'работать глубокой ночью, с полуночи до {NIGHT_END_HOUR} утра, — {{n}}',
                          ['ночь', 'ночи', 'ночей']),
        },
        # The metric behind each achievement in plain technical words and its unit, for the insights mode.
        'ach_metrics': {
            'phoenix': ('больше всего компактов в одной сессии', ''),
            'flawless': ('больше всего вызовов тулов в сессии без единой ошибки', ''),
            'warlord': ('больше всего сабагентов (Agent, Task) в одной сессии', ''),
            'marathon': (f'самый длинный отрезок работы героя без пауз дольше {ACTIVE_GAP_CAP_SECONDS // 60} минут',
                         'ч'),
            'trek': (f'больше всего работы героя в одной сессии (паузы дольше {ACTIVE_GAP_CAP_SECONDS // 60} минут '
                     'не в счёт)', 'ч'),
            'tireless': ('самая длинная серия активных дней', ''),
            'versatile': ('больше всего разных школ скилов за один день', ''),
            'strategist': ('сессий с plan mode', ''),
            'polyglot': ('разных расширений у правленых файлов', ''),
            'explorer': ('разных проектов с репликами человека', ''),
            'night_owl': (f'ночей с репликами с 0:00 до {NIGHT_END_HOUR}:00', ''),
        },
        'auras': {
            'guard': ('Аура стража', 'каждое действие проходит проверку до удара'),
            'temper': ('Аура закалки', 'после каждого действия результат доводится до блеска'),
            'mentor': ('Аура наставника', 'к каждому приказу героя добавляется мудрый совет'),
            'dawn': ('Аура рассвета', 'каждый поход начинается с благословения'),
            'herald': ('Аура вестника', 'ни одно завершённое дело не остаётся без вести'),
            'seal': ('Аура печати', 'дозволения выдаются сами, без лишних вопросов'),
            'memory': ('Аура памяти', 'важное не теряется в забвении'),
        },
        'aura_tiers': ('Искра', 'Тлеющая', 'Ровная', 'Яркая', 'Сияющая'),
        'aura_dormant': 'Угасшая',
        'gold_tiers': ('Пустой кошель', 'Тощий кошель', 'Полный кошель', 'Сундук золота', 'Сокровищница',
                       'Драконья казна'),
        'camp_tiers': ('Без привалов', 'Редкие привалы', 'Частые привалы', 'Живёт у костра'),
        'treasury': {
            'gold_from': 'от {amount} монет за месяц',
            'gold_below': 'меньше {amount} монет за месяц',
            'camp_from': 'от {n} {noun} за месяц',
            'camp_forms': ['привала', 'привалов', 'привалов'],
            'camp_none': 'ни одного привала за месяц',
            'times': {2: 'вдвое', 3: 'втрое', 4: 'вчетверо'},
            'times_n': 'в {n} раза',
            'gold_open': 'Дальше — {name} II, III…: каждая следующая ступень — {times} больше золота.',
            'camp_open': 'Дальше — {name} II, III…: каждая следующая ступень — {times} больше привалов.',
        },
        'millions': ('{:g} млн', '{:g} млрд'),
        'alignments': {
            ('lawful', 'good'): ('Законопослушный добрый', 'паладин кодекса: живёт по правилам и проверяет каждый шаг'),
            ('neutral', 'good'): ('Нейтральный добрый', 'добрый странник: бережёт мир без лишних уставов'),
            ('chaotic', 'good'): ('Хаотичный добрый', 'вольный герой: правил мало, но и зла не творит'),
            ('lawful', 'neutral'): ('Законопослушный нейтральный', 'судья: устав превыше всего'),
            ('neutral', 'neutral'): ('Истинно нейтральный', 'равновесие: ни устава, ни бунта'),
            ('chaotic', 'neutral'): ('Хаотичный нейтральный', 'вольный дух: поступает, как видит'),
            ('lawful', 'evil'): ('Законопослушный злой', 'тиран: строгий устав и тяжёлая рука'),
            ('neutral', 'evil'): ('Нейтральный злой', 'наёмник: результат любой ценой'),
            ('chaotic', 'evil'): ('Хаотичный злой', 'разрушитель: без правил и без жалости'),
        },
        # Abbreviation, name, meaning, and for the insights mode the rule in words and the labels of its metrics.
        'attributes': {
            'str': ('СИЛ', 'Сила', 'сколько работы герой вывозит за один заход',
                    f'сколько правок (Edit, Write) в обычной сессии с правками; {STR_EDITS_MID} правок — это 10.5 '
                    'из 20',
                    ('правок в обычной сессии с правками', 'сессий с правками')),
            'dex': ('ЛОВ', 'Ловкость', 'точность: действия и правки без промахов',
                    f'среднее двух оценок: доля вызовов без ошибок и доля правок с первого раза; '
                    f'{DEX_SUCCESS_LO:.0%} — это 1 из 20, 100% — это 20',
                    ('вызовов без ошибок', 'правок с первого раза')),
            'con': ('ВЫН', 'Выносливость', 'долгие походы и серии дней без перерыва',
                    f'среднее трёх оценок: длина 10% самых долгих сессий ({CON_HOURS_MID:g} ч — это 10.5 из 20), '
                    f'компакты ({CON_COMPACTIONS_MID} — 10.5), текущая серия дней ({CON_STREAK_MID} — 10.5)',
                    ('10% самых долгих сессий', 'компактов', 'текущая серия дней')),
            'int': ('ИНТ', 'Интеллект', 'широта арсенала и тяга к знаниям',
                    f'среднее двух оценок: разных тулов, скилов и MCP в ходу ({INT_BREADTH_MID} — это 10.5 из 20) '
                    f'и обращений к докам на сессию ({INT_DOCS_MID} — 10.5)',
                    ('разных тулов, скилов и MCP в ходу', 'обращений к докам на сессию')),
            'wis': ('МДР', 'Мудрость', 'самостоятельность и взвешенность решений',
                    f'среднее трёх оценок: действий на реплику ({WIS_AUTONOMY_MID} — это 10.5 из 20), прерываний '
                    f'и отказов на реплику (0 — 20, {WIS_FRICTION_HI:g} и больше — 1), доля сессий с plan mode '
                    f'({WIS_PLAN_SHARE_MID:.0%} — 10.5)',
                    ('действий на реплику в обычной сессии', 'прерываний и отказов на реплику', 'сессий с plan mode')),
            'cha': ('ХАР', 'Харизма', 'влияние на мир за пределами кода',
                    f'коммиты, PR и исходящие вызовы MCP на активный день; {CHA_ACTIONS_MID} — это 10.5 из 20',
                    ('коммитов, PR, исходящих вызовов MCP', 'действий на активный день')),
        },
        'metric': {
            'of': '{part} из {whole}',
            'from_hours': 'от {hours} ч',
            'per_days': '{value} за {days} {noun}',
            'day_forms': ['день', 'дня', 'дней'],
        },
        'decimal': ',',
        'thousands': ' ',
        'card': {
            'headline': 'Уровень {level} · {name}',
            'title': '«{title}»',
            'heading': 'Герой Claude Code: {headline}',
            'avatar': 'Аватар героя',
            'xp': 'Опыт {into} из {need} до {next} уровня',
            'skills': 'Сильнейшие навыки',
            'gear': 'Снаряжение',
            'alignment': 'Характер',
            'medals': 'Медали: золото {gold} · серебро {silver} · бронза {bronze}',
            'prompt': 'Открой страницу героя',
            'button': 'Открыть страницу героя ↗',
        },
        # Tooling words a game alias must not use: the page speaks about the hero.
        'tooling': ['харнес', 'агент', 'клод', 'промпт', 'хук', 'скил', 'сесси', 'токен', 'claude'],
    },
    'en': {
        'ranks': ('Novice', 'Apprentice', 'Journeyman', 'Adept', 'Expert', 'Master', 'Grandmaster'),
        'rarities': {
            'common': 'common', 'uncommon': 'uncommon', 'rare': 'rare', 'epic': 'epic', 'legendary': 'legendary',
        },
        'schools': {
            'smith': (
                'Smith', 'forges code: features, refactoring, tests',
                'The school of the code craft. Here go the talents that help write, change and check code: the rules '
                'of the craft, tests and blanks, reviews, knowing how the modules are built. The Smith is strong when '
                'the hero often takes up the hammer — writes the new, reforges the old and tempers it with tests.',
            ),
            'ranger': (
                'Ranger', 'follows the trail: investigations, debugging, incidents',
                'The school of investigations. Here go the talents of finding causes: taking errors and incidents '
                'apart, reading tracks in logs and metrics, debugging, knowing how production is built. The Ranger '
                'is strong when the hero often follows the trail of trouble and finds where it came from.',
            ),
            'engineer': (
                'Engineer', 'builds and launches: builds, releases, deploys, infrastructure',
                'The school of building and launching. Here go the talents for releases and rollouts, branches, '
                'builds, installation and infrastructure. The Engineer is strong when the hero often builds, rolls '
                'out and repairs things under load.',
            ),
            'alchemist': (
                'Alchemist', 'distills meaning from data: queries, samples, analytics',
                'The school of data. Here go the talents for database queries, samples, analytics and charts. The '
                'Alchemist is strong when the hero often turns raw data into answers.',
            ),
            'bard': (
                'Bard', 'masters the word: texts for people — documents, articles, letters, reports',
                'The school of the word. Here go the talents where the text itself is the result for people: '
                'documents and articles, reports, letters and messages. The notes and errands the hero leads the '
                'retinue with do not go here — they belong to the Summoner. The Bard is strong when the hero writes '
                'a lot for others and can tell the story of what was done.',
            ),
            'summoner': (
                'Summoner', 'leads a retinue: companions, their errands and memory, setting up camp',
                'The school of the retinue. Here go the talents of leading companions and one\'s own gear: roles in '
                'the party, errands in turn and on a schedule, the notes and memory of the retinue, setting up camp. '
                'The Summoner is strong when the hero leads a retinue.',
            ),
            'wanderer': (
                'Wanderer', 'takes on everything beyond development: home, hobbies, personal matters',
                'The school of everything else. Here go the talents beyond development: home, hobbies, money, '
                'travel, personal matters. The Wanderer is strong when the hero helps outside of work too.',
            ),
        },
        'no_school': ('No school', 'talents that have no school yet'),
        'epithets': {
            'smith': 'Thoroughbred Smith',
            'ranger': 'Keen-eyed Ranger',
            'engineer': 'Brilliant Engineer',
            'alchemist': 'Wisest Alchemist',
            'bard': 'Peerless Bard',
            'summoner': 'Commanding Summoner',
            'wanderer': 'Eternal Wanderer',
        },
        'hybrids': {
            frozenset(('smith', 'ranger')): (
                'Bug Hunter', 'tracks a bug down and reforges the code at once so that it never comes back'),
            frozenset(('smith', 'engineer')): (
                'Mechanic', 'forges the parts and assembles a working machine out of them'),
            frozenset(('smith', 'alchemist')): (
                'Artificer', 'melts data into code: forges working tools out of numbers'),
            frozenset(('smith', 'bard')): (
                'Runescribe', 'writes code like text and text like code: every line has its word'),
            frozenset(('smith', 'summoner')): (
                'Golem Master', 'forges with the hands of companions: the retinue swings the hammer, the hero aims '
                'the blow'),
            frozenset(('smith', 'wanderer')): (
                'Wandering Smith', 'carries the anvil along: forges for work and for the home'),
            frozenset(('ranger', 'engineer')): (
                'Warden', 'holds the borders: spots trouble in the logs and mends the walls at once'),
            frozenset(('ranger', 'alchemist')): (
                'Herbalist', 'seeks the roots of trouble in data and heals them with queries and samples'),
            frozenset(('ranger', 'bard')): (
                'Chronicler', 'investigates and writes it down: every finding becomes a chronicle'),
            frozenset(('ranger', 'summoner')): (
                'Beastmaster', 'sends a pack of companions down the trail and gathers all they find'),
            frozenset(('ranger', 'wanderer')): (
                'Adventurer', 'follows the trail everywhere — at work and in life'),
            frozenset(('engineer', 'alchemist')): (
                'Technomancer', 'builds systems that live on data, and data that feeds the systems'),
            frozenset(('engineer', 'bard')): (
                'Herald', 'ships releases and proclaims them to the world: the build and the word go hand in hand'),
            frozenset(('engineer', 'summoner')): (
                'Commander', 'runs the construction: companions build, roll out and report back'),
            frozenset(('engineer', 'wanderer')): (
                'Inventor', 'fixes and builds everything — from production to a kitchen shelf'),
            frozenset(('alchemist', 'bard')): (
                'Stargazer', 'reads fate in numbers and retells it in plain words'),
            frozenset(('alchemist', 'summoner')): (
                'Necromancer', 'raises answers from the depths of data by the hands of summoned companions'),
            frozenset(('alchemist', 'wanderer')): (
                'Hedge Healer', 'brews potions from data — for work and for everyday life'),
            frozenset(('bard', 'summoner')): (
                'Enchanter', 'enchants with the word: every word is a spell, and the companions are the retinue'),
            frozenset(('bard', 'wanderer')): (
                'Minstrel', 'wanders with the word: writes about work and about everything under the sun'),
            frozenset(('summoner', 'wanderer')): (
                'Shaman', 'summons helper spirits for work and for home'),
        },
        'no_class': ('Recruit', 'the talents are not sorted into schools yet: the class appears once they are '
                     'marked'),
        'skill_fallback': 'Unnamed talent',
        'gear_fallback': 'Unnamed artifact',
        'slots': {
            'helmet': ('Helmet', 'watchfulness: logs, metrics, monitoring, infrastructure'),
            'amulet': ('Amulet', 'databases and data queries'),
            'horn': ('Horn', 'communication: messengers, mail, notifications'),
            'boots': ('Boots', 'the browser and journeys across the web'),
            'grimoire': ('Grimoire', 'knowledge: documentation, notes, knowledge bases'),
            'ring': ('Ring', 'tasks: trackers, projects, planning'),
            'gloves': ('Gloves', 'the code craft: repositories, builds, reviews'),
            'cloak': ('Cloak', 'files, documents and cloud storage'),
        },
        'bag': 'bag: everything that fits no slot',
        'medals': ('bronze', 'silver', 'gold'),
        'achievements': {
            'phoenix': ('Phoenix', 'survive {n} in one quest and keep going',
                        ['memory compression', 'memory compressions']),
            'flawless': ('Flawless', 'go through a quest of {n} without a single error', ['action', 'actions']),
            'warlord': ('Warlord', 'summon {n} in one quest', ['companion', 'companions']),
            'marathon': ('Marathoner', f'work {{n}} in a row — no pauses longer than {ACTIVE_GAP_CAP_SECONDS // 60} '
                         'minutes', ['hour', 'hours']),
            'trek': ('Long Trek', f'spend {{n}} at work in one quest — pauses longer than '
                     f'{ACTIVE_GAP_CAP_SECONDS // 60} minutes do not count', ['hour', 'hours']),
            'tireless': ('Tireless', 'work {n} in a row', ['day', 'days']),
            'versatile': ('Jack of All Trades', 'use the talents of {n} in one day', ['school', 'different schools']),
            'strategist': ('Strategist', 'make a plan first and only then act, in {n}', ['quest', 'quests']),
            'polyglot': ('Polyglot', 'edit files of {n}', ['type', 'different types']),
            'explorer': ('Worldwalker', 'work in {n}', ['place', 'different places']),
            'night_owl': ('Night Owl', f'work deep at night, from midnight to {NIGHT_END_HOUR} a.m., on {{n}}',
                          ['night', 'nights']),
        },
        'ach_metrics': {
            'phoenix': ('most compactions in one session', ''),
            'flawless': ('most tool calls in a session without a single error', ''),
            'warlord': ('most subagents (Agent, Task) in one session', ''),
            'marathon': ('the longest stretch of the hero\'s work without pauses longer than '
                         f'{ACTIVE_GAP_CAP_SECONDS // 60} minutes', 'h'),
            'trek': (f'most hero work in one session (pauses longer than {ACTIVE_GAP_CAP_SECONDS // 60} minutes do '
                     'not count)', 'h'),
            'tireless': ('the longest run of active days', ''),
            'versatile': ('most different skill schools in one day', ''),
            'strategist': ('sessions with plan mode', ''),
            'polyglot': ('different extensions of edited files', ''),
            'explorer': ('different projects with human turns', ''),
            'night_owl': (f'nights with turns from 0:00 to {NIGHT_END_HOUR}:00', ''),
        },
        'auras': {
            'guard': ('Aura of the Guard', 'every action is checked before the blow'),
            'temper': ('Aura of Tempering', 'after every action the result is polished to a shine'),
            'mentor': ('Aura of the Mentor', 'every order of the hero comes with a word of wise advice'),
            'dawn': ('Aura of Dawn', 'every quest begins with a blessing'),
            'herald': ('Aura of the Messenger', 'no finished deed goes without news'),
            'seal': ('Aura of the Seal', 'permissions grant themselves, without needless questions'),
            'memory': ('Aura of Memory', 'what matters is not lost to oblivion'),
        },
        'aura_tiers': ('Spark', 'Smoldering', 'Steady', 'Bright', 'Radiant'),
        'aura_dormant': 'Faded',
        'gold_tiers': ('Empty purse', 'Thin purse', 'Full purse', 'Chest of gold', 'Treasure vault',
                       'Dragon\'s hoard'),
        'camp_tiers': ('No rests', 'Rare rests', 'Frequent rests', 'Lives by the fire'),
        'treasury': {
            'gold_from': 'from {amount} coins a month',
            'gold_below': 'less than {amount} coins a month',
            'camp_from': 'from {n} {noun} a month',
            'camp_forms': ['rest', 'rests'],
            'camp_none': 'not a single rest a month',
            'times': {2: 'twice', 3: 'three times', 4: 'four times'},
            'times_n': '{n} times',
            'gold_open': 'Beyond — {name} II, III…: each next tier takes {times} as much gold.',
            'camp_open': 'Beyond — {name} II, III…: each next tier takes {times} as many rests.',
        },
        'millions': ('{:g}M', '{:g}B'),
        'alignments': {
            ('lawful', 'good'): ('Lawful good', 'a paladin of the code: lives by the rules and checks every step'),
            ('neutral', 'good'): ('Neutral good', 'a kind wanderer: guards the world without needless charters'),
            ('chaotic', 'good'): ('Chaotic good', 'a free hero: few rules, but no evil either'),
            ('lawful', 'neutral'): ('Lawful neutral', 'a judge: the charter above all'),
            ('neutral', 'neutral'): ('True neutral', 'balance: neither charter nor rebellion'),
            ('chaotic', 'neutral'): ('Chaotic neutral', 'a free spirit: acts as it sees fit'),
            ('lawful', 'evil'): ('Lawful evil', 'a tyrant: a strict charter and a heavy hand'),
            ('neutral', 'evil'): ('Neutral evil', 'a mercenary: results at any cost'),
            ('chaotic', 'evil'): ('Chaotic evil', 'a destroyer: no rules and no mercy'),
        },
        'attributes': {
            'str': ('STR', 'Strength', 'how much work the hero carries in one go',
                    f'how many edits (Edit, Write) in a typical session with edits; {STR_EDITS_MID} edits score 10.5 '
                    'of 20',
                    ('edits in a typical session with edits', 'sessions with edits')),
            'dex': ('DEX', 'Dexterity', 'precision: actions and edits without a miss',
                    f'the mean of two scores: the share of calls without errors and the share of edits right the '
                    f'first time; {DEX_SUCCESS_LO:.0%} scores 1 of 20, 100% scores 20',
                    ('calls without errors', 'edits right the first time')),
            'con': ('CON', 'Constitution', 'long quests and runs of days without a break',
                    f'the mean of three scores: the length of the longest 10% of sessions ({CON_HOURS_MID:g} h score '
                    f'10.5 of 20), compactions ({CON_COMPACTIONS_MID} — 10.5), the current run of days '
                    f'({CON_STREAK_MID} — 10.5)',
                    ('the longest 10% of sessions', 'compactions', 'current run of days')),
            'int': ('INT', 'Intelligence', 'the breadth of the arsenal and a thirst for knowledge',
                    f'the mean of two scores: different tools, skills and MCP in use ({INT_BREADTH_MID} score 10.5 '
                    f'of 20) and doc lookups per session ({INT_DOCS_MID} — 10.5)',
                    ('different tools, skills and MCP in use', 'doc lookups per session')),
            'wis': ('WIS', 'Wisdom', 'independence and well-weighed decisions',
                    f'the mean of three scores: actions per turn ({WIS_AUTONOMY_MID} score 10.5 of 20), interrupts '
                    f'and denials per turn (0 — 20, {WIS_FRICTION_HI:g} or more — 1), the share of sessions with '
                    f'plan mode ({WIS_PLAN_SHARE_MID:.0%} — 10.5)',
                    ('actions per turn in a typical session', 'interrupts and denials per turn',
                     'sessions with plan mode')),
            'cha': ('CHA', 'Charisma', 'influence on the world beyond the code',
                    f'commits, PRs and outbound MCP calls per active day; {CHA_ACTIONS_MID} score 10.5 of 20',
                    ('commits, PRs, outbound MCP calls', 'actions per active day')),
        },
        'metric': {
            'of': '{part} of {whole}',
            'from_hours': 'from {hours} h',
            'per_days': '{value} over {days} {noun}',
            'day_forms': ['day', 'days'],
        },
        'decimal': '.',
        'thousands': ',',
        'card': {
            'headline': 'Level {level} · {name}',
            'title': '“{title}”',
            'heading': 'Claude Code hero: {headline}',
            'avatar': 'Hero avatar',
            'xp': 'XP {into} of {need} to level {next}',
            'skills': 'Strongest talents',
            'gear': 'Gear',
            'alignment': 'Alignment',
            'medals': 'Medals: gold {gold} · silver {silver} · bronze {bronze}',
            'prompt': 'Open the hero page',
            'button': 'Open the hero page ↗',
        },
        'tooling': ['harness', 'agent', 'claude', 'prompt', 'hook', 'skill', 'session', 'token'],
    },
}


def plural(lang, count, forms):
    """Noun form for a count: three Russian forms (1 день, 2 дня, 5 дней) or two English ones."""
    if lang == 'ru':
        return ru_plural(count, *forms)
    return forms[0] if count == 1 else forms[1]


def ru_plural(count, one, few, many):
    """Russian noun form for a count: 1 день, 2 дня, 5 дней."""
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def named(thresholds, names):
    """A threshold table with names: ((threshold, name), ...), the shape next_step and open_tier read."""
    return tuple(zip(thresholds, names))


def school_texts(key, lang='ru'):
    """Name and short line of a school; a missing school is the group of skills without one."""
    words = TEXTS[lang]
    return words['schools'][key][:2] if key in SCHOOLS else words['no_school']


def achievement_criteria(template, forms, threshold, lang='ru'):
    """Criteria text for one medal: the threshold with the right noun form."""
    return template.replace('{n}', f'{threshold} {plural(lang, threshold, forms)}')


def grouped(number, lang='ru'):
    """An integer with its thousands grouped: 21 532 with a no-break space in Russian, 21,532 in English."""
    return f'{number:,}'.replace(',', TEXTS[lang]['thousands'])


def localized(shown, lang='ru'):
    """A ready number text with the decimal mark of the page language: 10,5 in Russian."""
    return shown.replace('.', TEXTS[lang]['decimal'])
