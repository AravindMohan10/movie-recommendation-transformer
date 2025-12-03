import React, { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { getMovieById } from "../Utils/api";

export default function ShareMoviePage() {
  const { movieId } = useParams();
  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!movieId) {
      setError("No movie specified");
      setLoading(false);
      return;
    }
    getMovieById(movieId)
      .then(setMovie)
      .catch((e) => setError(e?.message ?? "Movie not found"))
      .finally(() => setLoading(false));
  }, [movieId]);

  const posterUrl = movie?.poster_url ?? movie?.poster_path;
  const imgSrc = posterUrl
    ? (posterUrl.startsWith("http")
        ? posterUrl
        : `https://image.tmdb.org/t/p/w342${posterUrl.startsWith("/") ? posterUrl : `/${posterUrl}`}`)
    : `https://via.placeholder.com/342x513/1a1a1a/666?text=No+Poster`;

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6">
      {loading ? (
        <Loader2 className="w-10 h-10 text-teal-400 animate-spin" />
      ) : error || !movie ? (
        <div className="text-center">
          <p className="text-gray-400 mb-4">{error || "Movie not found"}</p>
          <Link
            to="/"
            className="text-teal-400 hover:text-teal-300"
          >
            Go to cine.ai
          </Link>
        </div>
      ) : (
        <>
          <div className="text-2xl font-bold mb-2 bg-gradient-to-r from-teal-300 to-blue-200 bg-clip-text text-transparent">
            cine.<span className="text-white">ai</span>
          </div>
          <p className="text-gray-400 text-sm mb-6">Recommended for you</p>
          <div className="max-w-sm w-full rounded-2xl overflow-hidden border border-teal-500/30 bg-white/5">
            <img
              src={imgSrc}
              alt={movie.title}
              className="w-full aspect-[2/3] object-cover"
            />
            <div className="p-4">
              <h1 className="text-xl font-semibold text-white">{movie.title}</h1>
              {movie.overview && (
                <p className="text-gray-400 text-sm mt-2 line-clamp-3">
                  {movie.overview}
                </p>
              )}
            </div>
          </div>
          <Link
            to="/get-started"
            className="mt-8 px-8 py-3 rounded-full bg-gradient-to-r from-teal-400 to-blue-500 text-white font-semibold hover:opacity-90 transition-opacity"
          >
            Get recommendations on cine.ai
          </Link>
        </>
      )}
    </div>
  );
}
