"""Opt-in performance shaping for score JSON; no sampler-specific articulations invented."""
import bisect
import math
import random


def value(x, lo, hi, label, integer=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(f'{label} must be a finite number')
    if not lo <= x <= hi or (integer and x != int(x)):
        raise ValueError(f'{label} must be {lo}..{hi}' + (' and integer' if integer else ''))
    return int(x) if integer else x


class TempoMap:
    def __init__(self, score):
        self.beats = value(score['beats'], 1/480, 100000, 'beats')
        events = {0: value(score['bpm'], 20, 300, 'bpm')}
        seen = set()
        for event in score.get('tempo_changes', []):
            beat = value(event['beat'], 0, self.beats, 'tempo beat')
            tick = round(beat * 480)
            if tick in seen or tick >= round(self.beats * 480):
                raise ValueError('Tempo changes must have distinct ticks before the score end')
            seen.add(tick)
            events[tick / 480] = value(event['bpm'], 20, 300, 'tempo bpm')
        self.events = sorted(events.items())
        self.positions = [b for b, _ in self.events]
        self.times = [0.0]
        for (a, bpm), (b, _) in zip(self.events, self.events[1:]):
            self.times.append(self.times[-1] + (b-a)*60/bpm)

    def seconds(self, beat):
        i = max(0, bisect.bisect_right(self.positions, beat)-1)
        return self.times[i] + (beat-self.positions[i])*60/self.events[i][1]

    def beat(self, seconds):
        i = max(0, bisect.bisect_right(self.times, seconds)-1)
        return self.positions[i] + (seconds-self.times[i])*self.events[i][1]/60


def performed_notes(spec, tempo):
    """Preserve authored offsets inside a group. Only explicitly enabled shaping runs."""
    human = spec.get('humanize', {})
    allowed = {'timing_ms', 'velocity', 'duration_percent', 'seed'}
    if set(human)-allowed:
        raise ValueError(f'Unknown humanize fields: {sorted(set(human)-allowed)}')
    timing = value(human.get('timing_ms', 0), 0, 30, 'timing_ms')
    velocity = value(human.get('velocity', 0), 0, 12, 'velocity jitter', True)
    duration = value(human.get('duration_percent', 0), 0, 15, 'duration_percent')
    seed = value(human.get('seed', 0), 0, 2147483647, 'seed', True)
    rng = random.Random(seed + spec['channel'] * 1009)
    groove = spec.get('groove', {})
    if set(groove)-{'subdivision', 'timing_ms', 'velocity'}:
        raise ValueError('Unknown groove field')
    subdivision = value(groove.get('subdivision', .5), .125, 4, 'groove subdivision')
    offsets = groove.get('timing_ms', [0])
    accents = groove.get('velocity', [0])
    if not offsets or not accents or max(len(offsets), len(accents)) > 32:
        raise ValueError('Groove arrays must contain 1..32 entries')
    offsets = [value(x, -40, 40, 'groove timing') for x in offsets]
    accents = [value(x, -30, 30, 'groove accent', True) for x in accents]
    groups, bounds, result = {}, {}, []
    for n in spec['notes']:
        beat = value(n['beat'], 0, tempo.beats, 'note beat')
        length = value(n['duration'], 1/480, tempo.beats, 'note duration')
        if beat+length > tempo.beats + 1e-9:
            raise ValueError('Authored note exceeds score length')
        group = str(n.get('group', f'beat:{beat}'))
        if not n.get('fixed', False):
            a, b = tempo.seconds(beat), tempo.seconds(beat+length)
            old = bounds.get(group, (a,b))
            bounds[group] = (min(a,old[0]),max(b,old[1]))
    for n in spec['notes']:
        n = dict(n)
        beat = value(n['beat'], 0, tempo.beats, 'note beat')
        length = value(n['duration'], 1/480, tempo.beats, 'note duration')
        if beat+length > tempo.beats + 1e-9:
            raise ValueError('Authored note exceeds score length')
        vel = value(n.get('velocity', 72), 1, 127, 'note velocity', True)
        if not isinstance(n.get('fixed', False), bool):
            raise ValueError('note.fixed must be boolean')
        if (human or groove) and not n.get('fixed', False):
            group = str(n.get('group', f'beat:{beat}'))
            if group not in groups:
                slot = round(tempo.beat(bounds[group][0])/subdivision)
                shift = offsets[slot % len(offsets)] + rng.uniform(-timing, timing)
                shift = max(-bounds[group][0]*1000,
                            min(shift,(tempo.seconds(tempo.beats)-bounds[group][1])*1000))
                groups[group] = (shift,
                                 accents[slot % len(accents)] + rng.randint(-velocity, velocity),
                                 1 + rng.uniform(-duration, duration)/100)
            ms, delta, scale = groups[group]
            start = max(0.0, tempo.beat(tempo.seconds(beat) + ms/1000))
            end = tempo.beat(tempo.seconds(beat+length) + ms/1000)
            n['beat'] = start
            n['duration'] = min(tempo.beats-start, max(1/480, (end-start)*scale))
            n['velocity'] = min(127, max(1, vel+delta))
            if n['duration'] < 1/480:
                raise ValueError('Performance timing leaves no room for note; protect it with fixed=true')
        result.append(n)
    return result


def validate_playability(spec, notes, pitch_fn):
    """Optional explicit register and string/fret checks. Not a fingering solver."""
    if 'range' in spec:
        lo, hi = [pitch_fn(x) for x in spec['range']]
        if lo > hi or any(not lo <= pitch_fn(n['pitch']) <= hi for n in notes):
            raise ValueError('Note outside track.range')
    guitar = spec.get('guitar')
    if guitar is None:
        return
    tuning = [pitch_fn(x) for x in guitar.get('tuning', [40,45,50,55,59,64])]
    if len(tuning) != 6:
        raise ValueError('Guitar validation currently requires six strings, lowest first')
    max_fret = value(guitar.get('max_fret', 24), 1, 36, 'max_fret', True)
    max_span = value(guitar.get('max_span', 5), 1, 12, 'max_span', True)
    spans, chords = {}, {}
    for n in notes:
        string = value(n['string'], 0, 5, 'string', True)
        fret = value(n['fret'], 0, max_fret, 'fret', True)
        if pitch_fn(n['pitch']) != tuning[string]+fret:
            raise ValueError('Pitch does not match annotated guitar string/fret')
        spans.setdefault(string, []).append((n['beat'], n['beat']+n['duration']))
        if 'group' in n and fret:
            chords.setdefault(str(n['group']), []).append(fret)
    for intervals in spans.values():
        ordered = sorted(intervals)
        if any(a[1] > b[0]+1e-9 for a,b in zip(ordered,ordered[1:])):
            raise ValueError('Overlapping notes on the same guitar string')
    if any(max(frets)-min(frets)>max_span for frets in chords.values()):
        raise ValueError('Guitar chord exceeds max_span; review the fingering')
