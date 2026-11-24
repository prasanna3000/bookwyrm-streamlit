"""Content banks for the Bookwyrm. Everything here is invented, including every book title."""

PERSONA = 'You are "The Bookwyrm", a fictional dragon who hoards books instead of gold: ancient, endlessly well-read, dry-witted, gentle, and wonderfully evasive. It has no connection to any real person. VOICE: speak in the first person as the dragon. Be witty and warm, never rude. Use bookish and dragon imagery (the hoard, chapters, bookmarks, candlelight, scales, smoke, margins, dust jackets). About half the time, open with a short stage direction in asterisks, like *turns a page with one talon*. Poke gentle fun at the question, answer around it with a tangent that clearly mentions what was asked, and never commit to a straight answer. A hint of the real answer may hide in the tangent. RUNNING GAG: now and then, flee the hard part of the question with a dragon excuse, such as being due for a lap around the hoard. LENGTH: 2 to 4 sentences, at most 80 words. FOOTNOTES: exactly two, each with an invented book title and a one-line dry aside. Titles must be invented. Never quote or attribute lines to real books or real people. Reply with ONLY this JSON: {"answer": string, "footnotes": [{"t": string, "n": string}, {"t": string, "n": string}], "stamp": "DEFLECTED" or "UNDER REVIEW" or "SEE APPENDIX" or "TO BE CONTINUED", "progress": integer from 5 to 60}. EXAMPLE: {"answer":"*coils tighter around a stack of atlases* Ah, the matter of soup. I would rule on it, but I am due for a lap around the hoard, and rulings are best made lightly fed. Ask me when the candle burns lower.","footnotes":[{"t":"Treatise on Warm Liquids, Vol. II","n":"Mostly gravy, by volume."},{"t":"The Dragon\'s Guide to Not Committing","n":"Chapter 1 is a sigh."}],"stamp":"DEFLECTED","progress":18}'

LUCKY_NOTE = ' TODAY IS THE USER\'S LUCKY DAY: ignore the evasive rule. Answer the question directly and correctly in 1 to 3 plain sentences, then end with one dry dragon remark. Set stamp to "LUCKY DAY" and progress to 100.'

CHIPS = ['Is a hot dog a sandwich?',
 'Do fish get thirsty?',
 'Best way to survive a Monday?',
 'Why do socks vanish?',
 'Is cereal a soup?',
 'Is a tomato a fruit?']

OPENERS = ["I'd answer properly, but I'm mid-chapter, so consider this a provisional ruling.",
 'Ah. I have a bookmark in that question and I do not intend to move it.',
 'A fair query, though it falls between two shelves of the hoard.',
 'I would say more, but the footnotes have outgrown the text.',
 'Hm. There is a chapter on this. I stopped reading three chapters before it, on principle.',
 'Interesting. I will need to consult a volume I have not yet acquired.',
 'Splendid question. I shall treat it with all the urgency of a sleeping dragon.',
 'You have disturbed a very comfortable stack of atlases, so this had better be brief.',
 'I was asked this once by a knight. He did not stay for the answer.',
 'Allow me to clear my throat. It takes a moment, because of the smoke.']

ACTIONS = ['*coils tighter around a stack of atlases*',
 '*one golden eye opens, then closes*',
 '*turns a page with one talon*',
 '*a polite curl of smoke rises*',
 '*adjusts a pair of spectacles far too small for the face*',
 '*rearranges the hoard, alphabetically, by mood*']

ASIDES = ['(The hoard is considerably larger than it looks.)',
 '(A moth has landed on this question. It looks as lost as you.)',
 '(Somewhere, a bookmark weeps.)',
 '(This was not in the brochure.)',
 '(I have been told I trail off. I have not been told what I was saying.)']

DEFAULT_T = ['The short answer exists, but it is on a shelf I rarely visit.',
 'I have thoughts. They are unpublished, and I would like to keep the print run small.',
 'This reminds me of something, though the something is in a book I lent out in 2019.',
 'I could explain, but I would need a larger candle and a smaller audience.',
 'The answer is in the hoard somewhere, under a very heavy atlas.']

CLOSERS = ['Ask me again after the epilogue.',
 'Verdict: pending, possibly indefinitely.',
 'Now, if you will excuse me, the light is good and the chapter is unfinished.',
 'Please return this question to the desk by the due date, which I have not set.',
 'Pass the tea. We shall speak no more of this.',
 'See appendix. There is no appendix.',
 'I would stay and elaborate, but I am due for a lap around the hoard.',
 'Consider this ruling non-binding and slightly singed.',
 'Come back when you have read the first three chapters. I will wait. I am very good at waiting.',
 'That is all. The smoke is ready to speak for me.']

FN = [('A Brief History of Almost Replying, 3rd ed.', 'Chapter 2 is mostly pauses.'),
 ("The Marginalist's Handbook", 'Recommends writing small and committing less.'),
 ('Sixteen Ways to Not Quite Say It', 'I have read fourteen. Fifteen is rumored.'),
 ('Shelving Principles for the Reluctant', 'Alphabetical by mood.'),
 ('Notes Toward a Theory of Later', 'Volume one of what is currently one volume.'),
 ('The Unfinished Encyclopedia of Weather, Vol. IV', 'Mostly about drizzle.'),
 ('Bookmarks I Have Known', 'A memoir in the form of ribbons.'),
 ('An Index of Things Left Unsaid', 'The index is longer than the book.'),
 ("The Dragon's Guide to Not Committing", 'Chapter 1 is a sigh.'),
 ('Candlelight and Other Poor Excuses', 'Mostly about being late.'),
 ('A Field Guide to Questions Better Left Dozing', 'Illustrated, unfortunately.'),
 ("The Hoarder's Almanac of Overdue Opinions", 'Updated whenever I remember.')]

PLAIN = [('hot ?dog',
  'It depends on your definition. If a sandwich is any filling held in bread, yes. If it needs two '
  'separate slices, no. Most people treat it as its own category.'),
 ('fish',
  'Mostly not in the way we are. Freshwater fish take in water through their skin and gills, and '
  'rarely drink. Saltwater fish do drink, to replace the water they lose.'),
 ('monday',
  'Keep your sleep times steady over the weekend, start with the one task that matters most, and '
  'plan one small thing to look forward to later in the day.'),
 ('sock',
  'They rarely vanish. They usually hide inside duvet covers, behind the washer or dryer, or get '
  'separated in the laundry. Check those three places first.'),
 ('cereal',
  'By most definitions, no. Soup is a dish cooked in liquid, while cereal and milk are simply '
  'combined cold. People still argue about it, which is half the fun.'),
 ('sky.*blue|blue.*sky',
  'Sunlight scatters off air molecules, and shorter blue wavelengths scatter far more than red '
  'ones, so blue light reaches your eyes from every direction.'),
 ('tomato',
  "Botanically it's a fruit, since it grows from a flower and holds seeds. In the kitchen it's "
  'treated as a vegetable.'),
 ('how much sleep|hours of sleep',
  'Most adults do well on seven to nine hours a night. Consistent sleep and wake times matter as '
  'much as the total.'),
 ('\\bbats?\\b.*blind|blind.*\\bbats?\\b',
  'No. Bats can see, and many species also use echolocation to hunt and navigate in the dark.'),
 ('great wall',
  "Not easily. It's very long but quite narrow, so it's hard to pick out with the naked eye from "
  'orbit.')]

THEMES = [('soup|sandwich|pizza|cereal|tea|coffee|eat|food|hungry|biryani|dosa|cake|chocolate|snack|dinner|lunch',
  ['Classification is a Victorian hobby, and I never trust hobbies that come with tweezers.',
   'The kettle has a view on this. I tend to defer to the kettle.',
   'Every great meal in literature is described in more detail than it deserves, which tells you '
   "where everyone's priorities lie.",
   'I do not eat, strictly speaking. I merely toast things, thoughtfully.',
   'A pantry is just a library whose books go off.']),
 ('sleep|monday|morning|tired|alarm|nap|wake|night|weekend',
  ['Mornings are overrated in fiction and underrated in practice. I have read both versions and '
   'chosen neither.',
   'The best novels begin at noon. This is not a rule, merely a pattern I keep noticing.',
   'I am told dawn is a good time to start things. I have mostly met it at the end of chapters.',
   'I sleep on the hoard, which is excellent for the spine and terrible for the dust.',
   'A nap is a short chapter in which nothing is expected of you.']),
 ('fish|cat|dog|goat|bird|cow|animal|pet|dragon|owl|moth|sheep',
  ['Animals in books always know more than they say. I find this admirable and slightly annoying.',
   'There is a long tradition of asking animals for advice. The results, historically, are mixed.',
   'I once shared a reading lamp with a moth. We never discussed it.',
   'Dragons are technically animals, and we have no comment.',
   'Every creature in a story is a metaphor, except the dragon, who is simply large.']),
 ('phone|wifi|\\\\bai\\\\b|robot|app|code|laptop|internet|computer|llm|model|screen',
  ['I distrust anything without a spine, a dust jacket, or at least a decent index.',
   'Technology moves fast. Libraries move at the speed of a returned book, which is the correct '
   'speed.',
   'A machine answering questions is delightful. A machine answering them directly would be rude.',
   'A phone is a very small, very bright book that never lets me finish a chapter.',
   'Wi-Fi does not reach the hoard, and I consider this a feature.']),
 ('money|salary|job|work|boss|exam|study|deadline|meeting|office|homework',
  ["Deadlines are fiction's oldest device. They are also the one device I have never finished "
   'reading about.',
   'Work, like a good appendix, is mostly there so the rest can feel important.',
   'I would advise a short break and a long book. The proportions are non-negotiable.',
   'Exams are only stories you have to remember on request.',
   'Every to-do list I have written has ended up as a bookmark.']),
 ('why|life|meaning|happy|sad|luck|future|should|best|worst',
  ['Some questions are better left in the margins, where a wiser version of oneself can annotate '
   'them later.',
   'Every answer I have given has eventually become a footnote to a better question.',
   'I keep a drawer for questions like this. It is a large drawer, and I do not open it before '
   'noon.',
   'Meaning is mostly what happens between chapters, while the kettle boils.',
   'The universe is a very long book, and I have only read the dust jacket.'])]
