"""Regular expressions to be run against patch metadata for determining possible tags."""

TAGS_NAMES = {
    'Accordion': r'acc(ord.on|\b)',
    'Acid': r'acid|303',
    'Acoustic': r'acoustic',
    'Air': r'\bair',
    'Arp': r'[^h]arp|peggi',
    'Bass': r'^((?!drum).)*bass(?!oon)|\bb[as]\b',
    'Bell': r'bell(s|z|\b)',
    'Brass': r'bra?s|horn|trumpet|trombone',
    'Breath': r'breath',
    'Build': r'\bbuild',
    'Choir': r'choir',
    'Clap': r'clap',
    'Clav': r'clav',
    'Crash & Sweep': r'crash|sweep',
    'Cymbal': r'crash|cym(bal)?|\bride|\brd\b',
    'Drop': r'\bdrop',
    'Drum': r'dru?m|snar|tom|kic?k|taiko|timpani',
    'Flanger': r'flang',
    'FM': r'fm',
    'FX': r'fx|\bhit|effect|echo\b|noise|drone',
    'Guitar': r'-string\b|g(u?i)?ta?r|pick',
    'Harp': r'\bharp(?!si)',
    'Harpsichord': r'harpsi',
    'Hat': r'(hi-?|\b)hat(s|z|\b)|(((closed|open).?)|(?=.*?cym).*)hi',
    'Horn': r'horn|trumpet|trombone',
    'Keys': r'\bke?y',
    'Kick': r'kic?k',
    'Lead': r'lead|\bld\b|le?a?d.?(]|:)',
    'Lo-fi': r'lo-?fi',
    'Mono': r'mono',
    'Organ': r'\borg|wurl',
    'Pad': r'pa?d',
    'Percussion': r'pe?rc|tamb',
    'Piano': r'piano',
    'Pizzicato': r'pizz(i|\b|.cato)',
    'Pluck': r'pl(u|c|uc)?k',
    'Poly': r'poly',
    'PWM': r'pwm',
    'Reverse': r'reverse',
    'Ride': r'ride|\brd\b',
    'Saw': r'saw',
    'Sitar': r'sitar',
    'Snare': r'snar',
    'Square': r'square',
    'Stab': r'\bstab',
    'Steel Drum': r'^(?!.*?(?:g(u?i)?ta?r|pick|string)).*steel',
    'String': r'(?!-)string|cello|violin|fiddle',
    'Sub': r'sub',
    'Tom': r'tom',
    'Triangle': r'triang',
    'Trombone': r'trombone',
    'Trumpet': r'trumpet',
    'Voice': r'choir|voice|voc(?!oder)|vox|goblin',
    'Wah': r'wah',
    'Whistle': r'whistl',
    'Wind': r'wi?nd|clarinet|flute|piccolo|recorder|bassoon',
    'Wood': r'wood',
}
