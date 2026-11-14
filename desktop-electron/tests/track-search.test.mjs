import assert from 'node:assert/strict';
import test from 'node:test';
import * as model from '../.out/renderer/model.js';
import {
  TRACK_SEARCH_LIMIT, clearedTrackMessage, nextActiveIndex, searchResultMessage, searchTracks,
  selectedTrackMessage, trackChoiceArtist, trackChoiceBpm, trackChoiceKey, trackChoiceLabel,
  trackChoiceMeta, trackChoiceTitle, unavailableTrackLabel,
} from '../.out/renderer/track-search.js';

const tracks = [
  { id: 'a'.repeat(64), title: 'Brújula', artist: 'Björk', bpm: 124, key: '8A', genre: 'Deep House', energy: 6 },
  { id: 'b'.repeat(64), title: 'Midnight', artist: 'Other', bpm: 126, key: '9B', genre: 'Techno', energy: 7 },
  { id: 'c'.repeat(64), title: 'Ámbar', artist: 'Somebody', bpm: 124, key: null, genre: 'House', energy: null },
  { id: 'd'.repeat(64), title: 'Sin datos', artist: 'Nadie', bpm: null, key: null, energy: null },
];
const ids = (list) => list.map((track) => track.id);
const many = Array.from({ length: 30 }, (_, index) => ({ id: index.toString(16).padStart(64, '0'), title: `Mix ${index}`, artist: 'DJ', bpm: 120 + index, key: '8A' }));
// The matcher this change replaces, kept verbatim so the library box can be compared against it.
const previousFilter = (list, query, metadata) => {
  const search = query.trim().toLocaleLowerCase();
  return list.filter((track) => {
    const match = `${track.title} ${track.artist} ${track.key ?? ''} ${track.genre ?? ''}`.toLocaleLowerCase().includes(search);
    return match && (metadata === 'all' || model.hasPrepMetadata(track) === (metadata === 'ready'));
  });
};

test('opening-track search matches title, artist, key, genre and BPM without case or accent sensitivity', () => {
  assert.deepEqual(ids(searchTracks(tracks, 'brujula').results), [tracks[0].id]);
  assert.deepEqual(ids(searchTracks(tracks, 'BJÖRK').results), [tracks[0].id]);
  assert.deepEqual(ids(searchTracks(tracks, 'AMBAR').results), [tracks[2].id]);
  assert.deepEqual(ids(searchTracks(tracks, '9b').results), [tracks[1].id]);
  assert.deepEqual(ids(searchTracks(tracks, 'deep house').results), [tracks[0].id]);
  assert.deepEqual(ids(searchTracks(tracks, '124').results), [tracks[0].id, tracks[2].id]);
  assert.deepEqual(ids(searchTracks(tracks, '  techno  ').results), [tracks[1].id]);
  for (const empty of ['', '   ']) assert.deepEqual(searchTracks(tracks, empty), { results: [], total: 0 });
  assert.deepEqual(searchTracks(tracks, 'zzz'), { results: [], total: 0 });
});

test('opening-track search lists at most ten tracks in stable library order and reports the real total', () => {
  const found = searchTracks(many, 'mix');
  assert.equal(TRACK_SEARCH_LIMIT, 10);
  assert.equal(found.results.length, 10);
  assert.equal(found.total, 30);
  assert.deepEqual(ids(found.results), ids(many.slice(0, 10)));
  assert.deepEqual(ids(searchTracks(many, 'mix').results), ids(searchTracks(many, 'mix').results));
  assert.equal(searchTracks(many, 'mix', 3).results.length, 3);
  assert.equal(searchTracks(many, 'mix', 3).total, 30);
  assert.deepEqual(ids(searchTracks([tracks[1], tracks[0]], 'b').results), [tracks[1].id, tracks[0].id], 'matches keep library order, not query order');
});

test('keyboard navigation wraps around every available option and is inert without options', () => {
  assert.equal(nextActiveIndex(-1, 1, 3), 0);
  assert.equal(nextActiveIndex(-1, -1, 3), 2);
  assert.equal(nextActiveIndex(0, 1, 3), 1);
  assert.equal(nextActiveIndex(2, 1, 3), 0);
  assert.equal(nextActiveIndex(0, -1, 3), 2);
  for (const delta of [1, -1]) assert.equal(nextActiveIndex(0, delta, 0), -1);
});

test('option lines and the selected chip show real title, artist, BPM and key with Spanish gaps', () => {
  assert.equal(trackChoiceTitle(tracks[3]), 'Sin datos');
  assert.equal(trackChoiceTitle({ ...tracks[3], title: '' }), 'Sin título');
  assert.equal(trackChoiceArtist({ ...tracks[3], artist: '' }), 'Artista desconocido');
  assert.equal(trackChoiceBpm(tracks[0]), '124 BPM');
  assert.equal(trackChoiceBpm({ ...tracks[0], bpm: 0 }), 'Sin BPM');
  assert.equal(trackChoiceBpm(tracks[3]), 'Sin BPM');
  assert.equal(trackChoiceKey(tracks[0]), '8A');
  assert.equal(trackChoiceKey(tracks[3]), 'Sin tonalidad');
  assert.equal(trackChoiceLabel(tracks[0]), 'Brújula · Björk');
  assert.equal(trackChoiceMeta(tracks[0]), '124 BPM · 8A');
  assert.equal(trackChoiceMeta(tracks[3]), 'Sin BPM · Sin tonalidad');
  assert.equal(unavailableTrackLabel('f'.repeat(64)), 'No disponible: ffffffff');
});

test('result counts, selection and clearing are announced in Spanish and silent before typing', () => {
  assert.equal(searchResultMessage('', 0, 0), '');
  assert.equal(searchResultMessage('  ', 0, 0), '');
  assert.equal(searchResultMessage(' zzz ', 0, 0), 'Sin coincidencias para «zzz».');
  assert.equal(searchResultMessage('house', 1, 1), '1 coincidencia. Usa las flechas para moverte y Enter para elegir.');
  assert.equal(searchResultMessage('house', 4, 4), '4 coincidencias. Usa las flechas para moverte y Enter para elegir.');
  assert.equal(searchResultMessage('house', 10, 30), 'Mostrando 10 de 30 coincidencias. Usa las flechas para moverte y Enter para elegir.');
  assert.equal(selectedTrackMessage('Brújula · Björk'), 'Pista de apertura: Brújula · Björk.');
  assert.equal(clearedTrackMessage(), 'Sin preferencia de apertura.');
});

test('the library search box keeps every previous result and only gains BPM and accent-insensitive matches', () => {
  for (const query of ['björk', 'BJÖRK', 'midnight', '9b', '', '   ', 'techno']) {
    for (const metadata of ['all', 'ready', 'incomplete']) assert.deepEqual(model.filterTracks(tracks, query, metadata), previousFilter(tracks, query, metadata), `${query} / ${metadata}`);
  }
  assert.equal(previousFilter(tracks, '124', 'all').length, 0);
  assert.deepEqual(ids(model.filterTracks(tracks, '124', 'all')), [tracks[0].id, tracks[2].id]);
  assert.equal(previousFilter(tracks, 'bjork', 'all').length, 0);
  assert.deepEqual(ids(model.filterTracks(tracks, 'bjork', 'all')), [tracks[0].id]);
  assert.deepEqual(ids(model.filterTracks(tracks, 'sin tonalidad', 'all')), [], 'missing metadata is never invented as search text');
  assert.equal(tracks.length, 4, 'filtering never changes the source library');
});
