const path = require('path');
const express = require('express');
const cors = require('cors');

require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const apiRoutes = require('./routes/api');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:5173'],
  credentials: true,
}));
app.use(express.json());

app.use('/api', apiRoutes);

app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: err.message || 'Internal server error',
  });
});

app.listen(PORT, () => {
  console.log(`Express API proxy listening on http://localhost:${PORT}`);
});
