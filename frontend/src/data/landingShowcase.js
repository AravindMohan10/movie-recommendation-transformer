/** Curated landing-page queues — poster + copy stay in sync. */

export const SHOWCASE_QUEUES = [
  {
    confidence: "High confidence",
    movies: [
      {
        id: "shutter-island",
        title: "Shutter Island",
        poster_url: "https://image.tmdb.org/t/p/w342/nrmXQ0zcZUL8jFLrakWc90IR8z9.jpg",
        reason:
          "You've liked psychological thrillers with unreliable narrators. Shutter Island stays claustrophobic until the final turn — same dread, tighter pacing.",
      },
      {
        id: "prisoners",
        title: "Prisoners",
        poster_url: "https://image.tmdb.org/t/p/w342/uhviyknTT5cEQXbn6vWIqfM4vGm.jpg",
      },
      {
        id: "zodiac",
        title: "Zodiac",
        poster_url: "https://image.tmdb.org/t/p/w342/6YmeO4pB7XTh8P8F960O1uA14JO.jpg",
      },
    ],
  },
  {
    confidence: "High confidence",
    movies: [
      {
        id: "arrival",
        title: "Arrival",
        poster_url: "https://image.tmdb.org/t/p/w342/x2FJ7tcl6DVMsisWHmpIHZMpYM8.jpg",
        reason:
          "You save contemplative sci-fi over spectacle. Arrival is built on language and grief — the kind of slow-burn you keep coming back to.",
      },
      {
        id: "interstellar",
        title: "Interstellar",
        poster_url: "https://image.tmdb.org/t/p/w342/6ELJEzQJ3Y45HczvreC3dg0GV5R.jpg",
      },
      {
        id: "blade-runner-2049",
        title: "Blade Runner 2049",
        poster_url: "https://image.tmdb.org/t/p/w342/gajvaN1LiSV1KNwwZoGirIK3zQ0.jpg",
      },
    ],
  },
  {
    confidence: "Mixed confidence",
    movies: [
      {
        id: "parasite",
        title: "Parasite",
        poster_url: "https://image.tmdb.org/t/p/w342/7IiTTgloJzvGI1WAMzqwXlbVJ1H.jpg",
        reason:
          "Your reviews mention class tension and sharp tonal shifts. Parasite moves from satire to thriller without losing control — a strong match.",
      },
      {
        id: "memories-of-murder",
        title: "Memories of Murder",
        poster_url: "https://image.tmdb.org/t/p/w342/jcgUjx1QcupGzjntTVlnQ15lHqy.jpg",
      },
      {
        id: "get-out",
        title: "Get Out",
        poster_url: "https://image.tmdb.org/t/p/w342/tFXcEccSQMf3lfhfXKSU9iRBpa3.jpg",
      },
    ],
  },
];

export const SHOWCASE_POSTERS = SHOWCASE_QUEUES.flatMap((q) =>
  q.movies.map(({ id, title, poster_url }) => ({ id, title, poster_url }))
);

export function getShowcaseQueueForToday() {
  const dayKey = Math.floor(Date.now() / 86400000);
  return SHOWCASE_QUEUES[dayKey % SHOWCASE_QUEUES.length];
}
