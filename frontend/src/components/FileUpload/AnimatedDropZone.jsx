import { motion, AnimatePresence } from 'framer-motion';
import { Upload, File } from 'lucide-react';
import { useState } from 'react';

export const AnimatedDropZone = ({ onFileSelect, isUploading = false, uploadProgress = 0 }) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  return (
    <motion.div
      className={`scan-line relative overflow-hidden rounded-xl border-2 border-dashed p-12 text-center transition-all duration-300 cursor-pointer ${
        isDragging
          ? 'border-blue-400 bg-blue-500/10'
          : 'border-slate-600 hover:border-slate-500'
      }`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{
        opacity: 1,
        scale: isDragging ? 1.02 : 1,
      }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Animated Background Particles */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        animate={isDragging ? { opacity: 1 } : { opacity: 0 }}
      >
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-blue-400 rounded-full"
            initial={{
              x: Math.random() * 100 + '%',
              y: Math.random() * 100 + '%',
              scale: 0
            }}
            animate={{
              y: [null, '-100%'],
              scale: [0, 1, 0],
              opacity: [0, 1, 0]
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: i * 0.1,
              ease: 'easeOut'
            }}
          />
        ))}
      </motion.div>

      <AnimatePresence mode="wait">
        {isUploading ? (
          <motion.div
            key="uploading"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-4"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            >
              <Upload className="w-16 h-16 mx-auto text-blue-400" />
            </motion.div>
            <div className="space-y-2">
              <p className="text-lg font-semibold text-white">Uploading...</p>
              <div className="w-64 mx-auto h-2 bg-slate-800 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
                  initial={{ width: 0 }}
                  animate={{ width: `${uploadProgress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="idle"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            <motion.div
              animate={{
                y: [0, -15, 0],
                rotate: isDragging ? [0, 360] : 0
              }}
              transition={{
                y: { repeat: Infinity, duration: 2.5, ease: 'easeInOut' },
                rotate: { duration: 0.6 }
              }}
            >
              <File className="w-24 h-24 mx-auto text-blue-400" />
            </motion.div>

            <div className="space-y-2">
              <h3 className="text-2xl font-bold text-white">
                Drop your file here
              </h3>
              <p className="text-slate-400">
                or click to browse from your computer
              </p>
              <motion.button
                type="button"
                className="mt-4 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg font-semibold"
                whileHover={{ scale: 1.05, boxShadow: '0 10px 40px rgba(59,130,246,0.4)' }}
                whileTap={{ scale: 0.95 }}
              >
                Choose File
              </motion.button>
            </div>

            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-sm text-slate-500">
              <span>✓ PDF</span>
              <span>✓ DOCX</span>
              <span>✓ Images</span>
              <span>✓ Archives</span>
              <span>✓ Executables</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
