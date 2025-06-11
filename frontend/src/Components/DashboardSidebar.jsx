import React from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

const DashboardSidebar = ({ 
  recentActivity, 
  isOpen,
  onToggle 
}) => {
  return (
    <>
      {/* Toggle Button - Glassmorphism Style */}
      <motion.button
        onClick={onToggle}
        whileHover={{ scale: 1.1, boxShadow: "0 0 20px rgba(1,255,233,0.4)" }}
        whileTap={{ scale: 0.95 }}
        className={`fixed top-4 ${isOpen ? 'left-[260px]' : 'left-4'} z-[100] w-12 h-12 rounded-full backdrop-blur-xl bg-white/5 border border-teal-500/30 flex items-center justify-center text-teal-300 transition-all duration-300 shadow-lg`}
        style={{ 
          transition: 'left 0.3s ease',
          boxShadow: isOpen ? '0 0 20px rgba(1,255,233,0.2)' : '0 4px 12px rgba(0,0,0,0.3)'
        }}
      >
        <svg 
          width="16" 
          height="16" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2"
          className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
        >
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </motion.button>

      {/* Sidebar - Glassmorphism Design */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop blur overlay for mobile */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onToggle}
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-20 md:hidden"
            />
            
            <motion.aside
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed left-0 top-0 h-screen w-[260px] backdrop-blur-2xl bg-gradient-to-b from-white/5 via-white/5 to-black/20 border-r border-teal-500/20 z-30 overflow-hidden shadow-2xl"
              style={{
                boxShadow: 'inset 0 0 60px rgba(1,255,233,0.05), 4px 0 24px rgba(0,0,0,0.5)'
              }}
            >
              {/* Sidebar Header - Glassmorphism */}
              <div className="sticky top-0 backdrop-blur-xl bg-white/5 border-b border-teal-500/20 p-5 z-10">
                <h2 className="text-lg font-light text-white tracking-wide bg-gradient-to-r from-teal-200 to-blue-200 bg-clip-text text-transparent">
                  Activity
                </h2>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                  <Link
                    to="/my-reviews"
                    className="inline-flex items-center gap-1.5 text-sm text-teal-400 hover:text-teal-300 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    My Reviews
                  </Link>
                  <Link
                    to="/watchlist"
                    className="inline-flex items-center gap-1.5 text-sm text-teal-400 hover:text-teal-300 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z" />
                    </svg>
                    Watchlist
                  </Link>
                </div>
              </div>

              {/* Content - Recent Activity Only */}
              <div className="p-5 h-[calc(100vh-80px)] overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(20, 184, 166, 0.3) transparent' }}>
                {recentActivity.length > 0 ? (
                  <div className="space-y-3">
                    {recentActivity.slice(0, 10).map((activity, idx) => (
                      <motion.div 
                        key={idx} 
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.05 }}
                        className="group"
                      >
                        <div className="flex items-start gap-3 p-3 rounded-xl backdrop-blur-sm bg-white/5 border border-teal-500/10 hover:border-teal-500/30 hover:bg-white/10 transition-all duration-200">
                          <div className={`w-2 h-2 rounded-full flex-shrink-0 mt-2 ${
                            activity.type === 'like' ? 'bg-green-400 shadow-md shadow-green-400/50' :
                            activity.type === 'dislike' ? 'bg-red-400 shadow-md shadow-red-400/50' :
                            activity.type === 'favorite' ? 'bg-yellow-400 shadow-md shadow-yellow-400/50' :
                            'bg-blue-400 shadow-md shadow-blue-400/50'
                          }`}></div>
                          <div className="flex-1 min-w-0">
                            <p className="text-gray-200 text-sm font-light leading-relaxed">{activity.label}</p>
                            <p className="text-gray-500 text-xs mt-1">{activity.time}</p>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-400">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 border border-teal-500/20 flex items-center justify-center backdrop-blur-sm">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-teal-400">
                        <path d="M3 3h6v6H3zM15 3h6v6h-6zM3 15h6v6H3zM15 15h6v6h-6z"/>
                      </svg>
                    </div>
                    <p className="text-sm font-light">No activity yet</p>
                    <p className="text-xs text-gray-500 mt-1">Like, review, or add movies to your watchlist to see them here.</p>
                  </div>
                )}
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
};

export default DashboardSidebar;
