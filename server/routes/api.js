const path = require('path');
const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const router = express.Router();

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const UPLOADS_DIR = path.join(__dirname, '..', '..', 'data', 'uploads');

if (!fs.existsSync(UPLOADS_DIR)) {
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });
}

const upload = multer({ dest: UPLOADS_DIR });

function fastApiErrorMessage(error, fallback) {
  if (error.response?.data) {
    const data = error.response.data;
    if (typeof data === 'string') return data;
    if (data.detail) {
      return Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
        : String(data.detail);
    }
    if (data.error) return String(data.error);
    return JSON.stringify(data);
  }
  if (error.code === 'ECONNREFUSED') {
    return 'Cannot reach Python API. Start FastAPI with: uvicorn src.api:app --reload --port 8000';
  }
  return error.message || fallback;
}

router.get('/health', async (req, res) => {
  try {
    const response = await axios.get(`${FASTAPI_URL}/health`, { timeout: 10000 });
    return res.json(response.data);
  } catch (error) {
    return res.status(502).json({
      success: false,
      error: fastApiErrorMessage(error, 'Health check failed'),
    });
  }
});

router.post('/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, error: 'No file provided' });
    }

    const form = new FormData();
    form.append('file', fs.createReadStream(req.file.path), {
      filename: req.file.originalname,
      contentType: req.file.mimetype || 'application/pdf',
    });

    const response = await axios.post(`${FASTAPI_URL}/upload`, form, {
      headers: form.getHeaders(),
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
      timeout: 120000,
    });

    try {
      fs.unlinkSync(req.file.path);
    } catch (_) {
      /* ignore cleanup errors */
    }

    return res.json(response.data);
  } catch (error) {
    if (req.file?.path) {
      try {
        fs.unlinkSync(req.file.path);
      } catch (_) {
        /* ignore */
      }
    }
    const status = error.response?.status || 500;
    return res.status(status).json({
      success: false,
      error: fastApiErrorMessage(error, 'Failed to upload file'),
    });
  }
});

router.post('/ask', async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_URL}/ask`, req.body, {
      timeout: 120000,
    });
    return res.json(response.data);
  } catch (error) {
    const status = error.response?.status || 500;
    return res.status(status).json({
      success: false,
      error: fastApiErrorMessage(error, 'Failed to process question'),
    });
  }
});

router.post('/summarize', async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_URL}/summarize`, req.body, {
      timeout: 180000,
    });
    return res.json(response.data);
  } catch (error) {
    const status = error.response?.status || 500;
    return res.status(status).json({
      success: false,
      error: fastApiErrorMessage(error, 'Failed to summarize document'),
    });
  }
});

router.post('/compare', async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_URL}/compare`, req.body, {
      timeout: 300000,
    });
    return res.json(response.data);
  } catch (error) {
    const status = error.response?.status || 500;
    return res.status(status).json({
      success: false,
      error: fastApiErrorMessage(error, 'Failed to compare strategies'),
    });
  }
});

router.post('/benchmark', async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_URL}/benchmark`, req.body, {
      timeout: 600000,
    });
    return res.json(response.data);
  } catch (error) {
    const status = error.response?.status || 500;
    return res.status(status).json({
      success: false,
      error: fastApiErrorMessage(error, 'Failed to run benchmark'),
    });
  }
});

module.exports = router;
