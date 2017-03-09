import pickle as pkl
import sys

import numpy as np
import pretty_midi


def parse_algorithm(alg_str):
    alg = {x: None for x in alg_str.strip().split()}
    if 'one-hot' in alg:
        alg['one-hot-dim'] = 0  # to be filled in
    return alg


def rotate(_chroma, semitone):
    if semitone == 0:
        return _chroma
    return np.concatenate((_chroma[-semitone:], _chroma[:_chroma.shape[0] - semitone]), axis=0)


def hamDis(chroma1, chroma2):
    assert chroma1.shape == chroma2.shape
    return float(np.count_nonzero(chroma1 != chroma2))


def union(chroma1, chroma2):
    assert chroma1.shape[0] == 12
    assert chroma2.shape[0] == 12
    ret = np.zeros(12)
    for i in range(12):
        if chroma1[i] and chroma2[i]:
            ret[i] = 1
    return ret

chroma2chord_LUT = np.array([
    [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
])


def closestChord(root, chordType):
    return rotate(chroma2chord_LUT[chordType].copy(), root)


def chroma2chord_v2(_chroma):
    # v2 is way faster
    notes = np.where(_chroma)[0]
    interval = np.diff(notes)
    if len(notes) == 3:
        if all(interval==np.array([4,3])): return [notes[0],1] #maj root position
        if all(interval==np.array([3,5])): return [notes[2],1] #maj 1st inversion
        if all(interval==np.array([5,4])): return [notes[1],1] #maj 2nd inversion
        if all(interval==np.array([3,4])): return [notes[0],2] #maj root position
        if all(interval==np.array([4,5])): return [notes[2],2] #maj 1st inversion
        if all(interval==np.array([5,3])): return [notes[1],2] #maj 2nd inversion
        return [0,6]
    if len(notes) == 4:
        if all(interval==np.array([4,3,4])): return [notes[0],3] #maj7 root position
        if all(interval==np.array([3,4,1])): return [notes[3],3] #maj7 1st inversion
        if all(interval==np.array([4,1,4])): return [notes[2],3] #maj7 2nd inversion
        if all(interval==np.array([1,4,3])): return [notes[1],3] #maj7 3rd inversion
        if all(interval==np.array([4,3,3])): return [notes[0],4] #dmn7 root position
        if all(interval==np.array([3,3,2])): return [notes[3],4] #dmn7 1st inversion
        if all(interval==np.array([3,2,4])): return [notes[2],4] #dmn7 2nd inversion
        if all(interval==np.array([2,4,3])): return [notes[1],4] #dmn7 3rd inversion
        if all(interval==np.array([3,4,3])): return [notes[0],5] #min7 root position
        if all(interval==np.array([4,3,2])): return [notes[3],5] #min7 1st inversion
        if all(interval==np.array([3,2,3])): return [notes[2],5] #min7 2nd inversion
        if all(interval==np.array([2,3,4])): return [notes[1],5] #min7 3rd inversion
        return [0,6]
    if len(notes) == 2:
        if all(interval==np.array([7])): return [notes[0],7] #power chord
        if all(interval==np.array([5])): return [notes[1],7] #power chord
        return [0,6]
    return [0,6]


def chroma2chord_v1(chroma):
    for i in range(12):
        chroma_shifted = rotate(chroma, i)
        if all(chroma_shifted == np.array([1,0,0,0,1,0,0,1,0,0,0,0])): return [(12-i)%12,1] #maj
        if all(chroma_shifted == np.array([1,0,0,1,0,0,0,1,0,0,0,0])): return [(12-i)%12,2] #min
        if all(chroma_shifted == np.array([1,0,0,0,1,0,0,1,0,0,0,1])): return [(12-i)%12,3] #maj7
        if all(chroma_shifted == np.array([1,0,0,0,1,0,0,1,0,0,1,0])): return [(12-i)%12,4] #7
        if all(chroma_shifted == np.array([1,0,0,1,0,0,0,1,0,0,1,0])): return [(12-i)%12,5] #min7
    return [0,0]


def isChord(notes):
    if len(notes) < 2:
        return False
    chord_list = []
    while len(notes) >= 2:
        if notes[0].start != notes[1].start or notes[0].end != notes[1].end:
            return False
        chord = []
        while len(notes) >= 2 and notes[0].start == notes[1].start and notes[0].end == notes[1].end:
            chord.append(notes[0])
            del notes[0]
        chord.append(notes[0])
        del notes[0]
        chord_list.append(chord)
    # assert len(notes) == 0
    return chord_list

_rootNote = {
    0: 'C', 1: 'C#', 2: 'D', 3: 'D#',
    4: 'E', 5: 'F', 6: 'F#', 7: 'G',
    8: 'G#', 9: 'A', 10: 'A#', 11: 'B',
}

_qualifier = {
    1: 'Maj', 2: 'Min', 3: 'Maj7', 4: '7', 5: 'Min7'
}


def printChord(_chroma):
    r, t = chroma2chord_v2(_chroma)
    S = _rootNote[r] + _qualifier[t] if t != 6 else 'N'
    print '%s\t' % S


def printChordProgression(y, cp):
    assert y.shape == cp.shape
    assert y.shape[1] == 128
    assert y.shape[2] == 12

    n_song = len(cp)
    for i in range(n_song):
        print 'song %d\t answ:' % i
        for j in range(8):
            printChord(y[i][16*j])
        print '\nsong %d\t pred:' % i
        for j in range(8):
            printChord(cp[i][16*j])
        print '\nsong %d\t diff:' % i
        cnt = 0
        for j in range(8):
            tmp = np.sum(abs(y[i][16*j]-cp[i][16*j]))
            cnt += tmp
            print '%d\t' % tmp
        print '%d\n' % cnt


def pred2chord(pred):
    pred = pred.reshape((pred.shape[0], 12, 8, pred.shape[1]/12/8))
    pred = np.mean(pred, axis=3)
    for i in range(len(pred)):
        for j in range(len(pred[0][0])):
            pred[i][:][:,j] = closestChord(pred[i][:][:,j])


def toCandidate(CP, allCP, bestN, criteria):
    ret = np.zeros_like(CP)
    bestIdx = np.zeros((len(CP), bestN), dtype=int)
    for i in range(len(CP)):
        minDis = sys.maxint
        minIdx = 0
        dis = np.zeros((len(allCP)))
        for j in range(len(allCP)):
            if criteria == 'L1':
                dis[j] = np.sum(abs(CP[i]-allCP[j]))
            elif criteria == 'L2':
                dis[j] = np.sqrt(np.sum(np.square(CP[i]-allCP[j])))
            else:
                print("Error in toCandidate function")
            if dis[j] < minDis:
                minDis = dis[j]
                minIdx = j
        ret[i] = allCP[minIdx]
        bestIdx[i] = np.argsort(dis)[:bestN]
    return ret, bestIdx


def toCandidateBestN(CP, allCP, bestN):
    bestIdx = np.zeros((len(CP), bestN), dtype=int)
    for i in range(len(CP)):
        dis = np.zeros((len(allCP)))
        for j in range(len(allCP)):
            dis[j] = np.sum(abs(CP[i]-allCP[j]))
        bestIdx[i] = np.argsort(dis)[:bestN]
    return bestIdx


def load_data(nb_test):
    C = np.genfromtxt('csv/chord.csv', delimiter=',')
    # Data in melody.csv and root.csv are represented as [0,11].
    # Thus, we first span it to boolean matrix
    M_dense = np.genfromtxt('csv/melody.csv', delimiter=',')
    M = np.zeros((M_dense.shape[0], M_dense.shape[1]*12))

    for i in range(M_dense.shape[0]):
        for j in range(M_dense.shape[1]):
            notes = int(M_dense[i][j])
            M[i][M_dense.shape[1]*notes+j] = 1
    M = np.swapaxes(M.reshape((M.shape[0], 12, 128)), 1, 2)
    C = np.swapaxes(C.reshape((C.shape[0], 12, 128)), 1, 2)
    m = M[:nb_test]
    c = C[:nb_test]
    M = M[nb_test:]
    C = C[nb_test:]
    return M, m, C, c

def get_XY(alg, M, C):
    if 'LM' in alg:
        if 'one-hot' in alg:
            with open('csv/chord-1hot-signatures.pickle', 'rb') as pfile:
                sign2chord = pkl.load(pfile)
                N = len(sign2chord)
                newC = np.zeros([C.shape[0] * 128, N])
                for i, x in enumerate(C.reshape([C.shape[0] * 128, 12])):
                    newC[i][sign2chord[str(x)]] = 1
                C = newC.reshape([C.shape[0], 128, N])
                alg['one-hot-dim'] = N
        return M, C

    assert 'pair' in alg
    n = M.shape[0]
    idx = np.random.randint(n, size=n)
    C_neg = C[idx]
    Ones = np.ones((n, 128, 1))
    Zeros = np.zeros((n, 128, 1))
    if 'L1' in alg or 'L2' in alg or 'F1' in alg or 'L1diff' in alg: # use L1 or L2 of two sources of chord as labels
        np.seterr(divide='ignore', invalid='ignore') # turn off warning of division by zero
        L1diff = np.abs(C - C_neg)
        L1 = np.sum(L1diff, 2)
        L1 = L1.reshape((n, 128, 1))
        L2 = np.sqrt(L1)
        p = np.sum(np.logical_and(C, C_neg), 2) / np.sum(C_neg, 2)
        r = np.sum(np.logical_and(C, C_neg), 2) / np.sum(C, 2)
        F1 = 2*p*r/(p+r)
        F1 = np.nan_to_num(F1.reshape((n, 128, 1)))
        if 'rand' in alg:
            X = np.concatenate((M, C_neg), 2)
            Y = L1 if 'L1' in alg else L2 if 'L2' in alg else F1 if 'F1' in alg else L1diff
        else:
            MC_neg = np.concatenate((M, C_neg), 2)
            MC = np.concatenate((M, C), 2)
            X = np.concatenate((MC, MC_neg), 0)
            Y = np.concatenate((Zeros, L1), 0) if 'L1' in alg \
            else np.concatenate((Zeros, L2), 0) if 'L2' in alg \
            else np.concatenate((Ones, F1), 0) if 'F1' in alg \
            else np.concatenate((np.tile(Zeros, 12), L1diff), 0)
        if 'L1' in alg or 'L2' in alg:
            Y = 1 - Y / 12.0
        if 'L1diff' in alg:
            Y = 1 - Y
    else:  # use 1 as positive labels and 0 as negative labels
        assert False
        MC = np.concatenate((M, C), 2)
        MC_neg = np.concatenate((M, C_neg), 2)
        X = np.concatenate((MC, MC_neg), 0)
        Y = np.concatenate((Ones, Zeros), 0)
    return X, Y


def get_test(alg, m, C):
    # x_te are the final testing features to match m to C
    m_rep, C_rep = rep(m, C)
    if 'pair' in alg:
        return np.concatenate((m_rep, C_rep), 2)
    elif 'LM' in alg:
        return m
    else:
        print('Error in get_test')


def print_result(pred, y, Y, alg, printCP, bestN):
    print '\nAlg: %s' % alg
    nb_test = pred.shape[0]
    if 'L2' in alg:
        pred, bestNIdx = toCandidate(pred, Y, bestN, 'L2')
        norm = np.sqrt(np.sum(np.square(pred - y))) / 128.0 / nb_test
    else:
        pred, bestNIdx = toCandidate(pred, Y, bestN, 'L1')
        norm = np.sum(abs(pred - y)) / 128.0 / nb_test
    numUniqIdx = len(np.unique(bestNIdx))
    if printCP:
        printChordProgression(y, pred)
    print 'num of unique idx  = %d/%d' % (numUniqIdx, nb_test)
    print 'norm after mapping = %.3f' % norm
    return bestNIdx, numUniqIdx, norm


def rep(m, C):
    nb_test = m.shape[0]
    nb_train = C.shape[0]
    C_rep = np.tile(C, (nb_test,  1, 1))
    m_rep = np.tile(m, (nb_train, 1, 1))
    m_rep = np.reshape(m_rep, (nb_train, nb_test, 128, 12))
    m_rep = np.swapaxes(m_rep, 1, 0)
    m_rep = np.reshape(m_rep, (nb_test * nb_train, 128, 12))
    return m_rep, C_rep

_note2int_dict = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4,
    'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9,
    'A#': 10, 'Bb': 10, 'B': 11,
}


def note2int(note):
    try:
        return _note2int_dict[note]
    except KeyError:
        print 'no match in note2int: ', note
        return 0

_mode2int_dict = {
    'Major': 0, 'Minor': 1, 'Dorian': 2, 'Phrygian': 3, 'Lydian': 4, 'Mixolydian': 5, 'Locryan': 6
}
_int2mode_dict = {
    0: 'Major', 1: 'Minor', 2: 'Dorian', 3: 'Phrygian', 4: 'Lydian', 5: 'Mixolydian', 6: 'Locryan'
}


def mode2int(mode):
    try:
        return _mode2int_dict[mode.title()]
    except KeyError:
        print 'no match in mode2int: ', mode
        return 0


def int2note(i):
    try:
        return _rootNote[i]
    except KeyError:
        print 'no match in int2note: ', i
        return 'C'


def int2mode(i):
    try:
        return _int2mode_dict[i]
    except KeyError:
        print 'no match in int2mode: ', i
        return 'Major'

_int2type = {
    0: 'Non-chord',
    1: 'Maj',
    2: 'Min',
    3: 'Maj7',
    4: 'Dominant7',
    5: 'Min7',
    6: 'omplex',  # complex chord, but not recognized
    7: 'power',  # power chord, but not recognized
}


def int2type(i):
    try:
        return _int2mode_dict[i]
    except KeyError:
        print 'no match in int2type: ', i
        return 'Non-chord'


def toMajKey(key, mode):
    if mode == 1:  # Minor to Major
        key = (key + 3) % 12
    elif mode == 2:  # Dorian to Major
        key = (key + 10) % 12
    elif mode == 3:  # Phrygian to Major
        key = (key + 8) % 12
    elif mode == 4:  # Lydian to Major
        key = (key + 7) % 12
    elif mode == 5:  # Mixolydian to Major
        key = (key + 5) % 12
    elif mode == 6:  # Locrian to Major
        key = (key + 1) % 12
    mode = 0
    return key, mode


def write_history(history, hist, epoch):
    history[0].append(epoch)
    history[1].append(round(hist.history['loss'][0], 2))
    history[2].append(round(hist.history['val_loss'][0], 2))
    history[3].append(round(hist.history['acc'][0], 2))
    history[4].append(round(hist.history['val_acc'][0], 2))
    return history


def Melody_Matrix_to_Section_Composed(melody_matrix):
    section = int(np.ceil(melody_matrix.shape[0] / 16.0))
    section_composed = np.zeros((section, 13), dtype=np.int)
    for m in xrange(128):
        mimax = np.amax(melody_matrix[m])
        mi = np.argmax(melody_matrix[m])
        if mimax == 0:
            section_composed[m/16][0] += 1
            continue
        for mm in xrange(12):
            if mm == mi:
                section_composed[m/16][mm+1] += 1
    return section_composed


def top3notes(chord):
    idx = np.argsort(chord)
    idx[idx < 9] = 0
    idx[idx >= 12-3] = 1
    return idx


def onehot2notes_translator():
    """
    generate a translator function that will map from a 1-hot repr of chord to a classical chord signature
    :return: f: the translator function
    """
    chord2sign = np.load('csv/chord-1hot-signatures-rev.npy')

    def f(chord):
        """
        :param chord: 1-hot representation of chords in (M, T, XDIM)
        :return: chord signature in (M, T, 12)
        """
        M, T, Dim = chord.shape
        res = np.empty([M*T, 12])
        for i, c in enumerate(chord.reshape([M*T, Dim])):
            id = np.nonzero(c)[0][0]
            res[i, :] = chord2sign[id]
        return res.reshape(M, T, 12)
    return f


def Matrices_to_MIDI(melody_matrix, chord_matrix):
    assert(melody_matrix.shape[0] == chord_matrix.shape[0])
    assert(melody_matrix.shape[1] == 12 and chord_matrix.shape[1] == 12)
       
    defaultMelOct = 5  # default melody octave
    defaultChrdOct = 3
    BPM = 160
    duration = 15.0/BPM
    m_start, c_start = 0, 0
    length = melody_matrix.shape[0]
    song = pretty_midi.PrettyMIDI()
    agp_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')  # use for chords
    bap_program = pretty_midi.instrument_name_to_program('Bright Acoustic Piano')  # use for melody
    melody = pretty_midi.Instrument(program=agp_program)
    chords = pretty_midi.Instrument(program=bap_program)
    
    for i in range(length):
        # Synthesizing melody
        m_note_nb_new = melody_matrix[i].tolist().index(1) if 1 in melody_matrix[i].tolist() else None
        if i == 0:
            m_note_nb_cur = m_note_nb_new
            m_time = 1
        elif m_note_nb_new == m_note_nb_cur:
            m_time += 1
        else:
            if m_note_nb_cur is not None:
                note = pretty_midi.Note(velocity=100, pitch=(m_note_nb_cur +12*(defaultMelOct + 1)) , start=m_start*duration, end=(m_start+m_time)*duration)
                melody.notes.append(note)
            m_start += m_time
            m_note_nb_cur = m_note_nb_new
            m_time = 1 
            
        # Synthesizing chord
        chords_new = np.where(chord_matrix[i] == 1)[0]
        if i == 0:
            chords_cur = chords_new
            c_time = 1
        elif np.array_equal(chords_cur, chords_new):
            c_time +=1 
        else:
            for n in chords_cur.tolist():
                note = pretty_midi.Note(velocity=100, pitch=(n + 12 * (defaultChrdOct + 1)),
                                        start=c_start * duration, end=(c_start + c_time) * duration)
                chords.notes.append(note)  
            c_start += c_time
            chords_cur = chords_new
            c_time = 1
        
    # Adding notes from last iteration        
    if m_note_nb_cur is not None:
        note = pretty_midi.Note(velocity=100, pitch=(m_note_nb_cur + 12 * (defaultMelOct + 1)),
                                start=m_start * duration, end=(m_start + m_time) * duration)
        melody.notes.append(note) 
    for n in chords_cur.tolist():
        note = pretty_midi.Note(velocity=100, pitch=(n + 12 * (defaultChrdOct + 1)),
                                start=c_start * duration, end=(c_start + c_time) * duration)
        chords.notes.append(note)  
           
    song.instruments.append(melody)
    song.instruments.append(chords)
    return song
