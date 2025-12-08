import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import { useState, type ChangeEvent } from 'react';
import { Box, Typography, Paper, Container, LinearProgress, Chip } from '@mui/material';
import { useNavigate } from 'react-router';
import { Upload, FileText, CheckCircle, Database } from 'lucide-react';
import { sourceService } from '../services/service-instances';

export default function Homepage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const navigate = useNavigate();

  const handleUpload = async (file: File | null) => {
    if (!file) {
      alert('Please select a file first.');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('import_now', 'true');
    formData.append('connection_id', '1');
    formData.append('eng_id', '');
    formData.append('eng_ids', JSON.stringify([]));

    for (const [key, value] of formData.entries()) {
      console.log(`${key}:`, value);
    }

    const resp = await sourceService.uploadCSV(formData);
    if (!resp) return;
    setUploading(false);
    navigate(`/graph?datasetId=${resp.dataset_id}`);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile);
      } else {
        alert('Please upload a CSV file');
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: '#ff6f00ff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 3
      }}
    >
      <Container maxWidth="md">
        <Paper
          elevation={24}
          sx={{
            padding: { xs: 3, md: 5 },
            borderRadius: 4,
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)'
          }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: '#555dfaff',
                mb: 2,
                boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)'
              }}
            >
              <Database size={40} color="white" />
            </Box>
            <Typography
              variant="h3"
              gutterBottom
              sx={{
                fontWeight: 700,
                background: '#666565ff',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                mb: 1
              }}
            >
              CSV Data Visualizer
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ fontSize: '1.1rem' }}>
              Upload your CSV file to generate an interactive graph visualization
            </Typography>
          </Box>
          <Box
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            sx={{
              border: dragActive ? '3px dashed #667eea' : '3px dashed #e0e0e0',
              borderRadius: 3,
              padding: 4,
              textAlign: 'center',
              backgroundColor: dragActive ? 'rgba(102, 126, 234, 0.05)' : 'rgba(0, 0, 0, 0.02)',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              mb: 3,
              '&:hover': {
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.05)'
              }
            }}
          >
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <Upload size={48} color={dragActive ? '#667eea' : '#999'} strokeWidth={1.5} />
              
              <Typography variant="h6" color={dragActive ? 'primary' : 'text.secondary'}>
                {dragActive ? 'Drop your file here' : 'Drag and drop your CSV file'}
              </Typography>
              
              <Typography variant="body2" color="text.secondary">
                or
              </Typography>

              <Button
                component="label"
                variant="outlined"
                startIcon={<FileText size={20} />}
                sx={{
                  borderRadius: 2,
                  textTransform: 'none',
                  fontSize: '1rem',
                  padding: '10px 30px',
                  borderWidth: 2,
                  '&:hover': {
                    borderWidth: 2
                  }
                }}
              >
                Browse Files
                <input
                  type="file"
                  hidden
                  accept=".csv"
                  onChange={handleFileChange}
                />
              </Button>

              <Typography variant="caption" color="text.secondary">
                Supported format: CSV files only
              </Typography>
            </Box>
          </Box>
          {file && (
            <Paper
              elevation={0}
              sx={{
                padding: 2.5,
                mb: 3,
                backgroundColor: '#f0f4ff',
                borderRadius: 2,
                border: '1px solid #d0d9ff'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <CheckCircle size={24} color="#667eea" />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body1" fontWeight={600} color="text.primary">
                    {file.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {formatFileSize(file.size)}
                  </Typography>
                </Box>
                <Chip
                  label="Ready"
                  color="success"
                  size="small"
                  sx={{ fontWeight: 600 }}
                />
              </Box>
            </Paper>
          )}
          {uploading && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Processing your file...
              </Typography>
              <LinearProgress
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: '#e0e0e0',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                    background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)'
                  }
                }}
              />
            </Box>
          )}
          <Button
            variant="contained"
            fullWidth
            size="large"
            onClick={() => handleUpload(file)}
            disabled={!file || uploading}
            sx={{
              height: 56,
              borderRadius: 2,
              fontSize: '1.1rem',
              fontWeight: 600,
              textTransform: 'none',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
              '&:hover': {
                background: 'linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%)',
                boxShadow: '0 6px 20px rgba(102, 126, 234, 0.5)'
              },
              '&:disabled': {
                background: '#e0e0e0',
                boxShadow: 'none'
              }
            }}
          >
            {uploading ? 'Processing...' : 'Upload & Visualize'}
          </Button>
          <Box sx={{ mt: 4, pt: 3, borderTop: '1px solid #e0e0e0' }}>
            <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ mb: 2 }}>
              What you'll get:
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
              <Chip label="Interactive Graph" variant="outlined" />
              <Chip label="Data Management" variant="outlined" />
              <Chip label="Visual Analytics" variant="outlined" />
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}