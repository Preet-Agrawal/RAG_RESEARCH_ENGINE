const { fastApiErrorMessage } = require('../api');

describe('fastApiErrorMessage', () => {
  it('returns the response body directly when it is a plain string', () => {
    const error = { response: { data: 'PDF is corrupted' } };
    expect(fastApiErrorMessage(error, 'fallback')).toBe('PDF is corrupted');
  });

  it('joins FastAPI/pydantic validation errors from a detail array', () => {
    const error = {
      response: {
        data: {
          detail: [
            { msg: 'field required' },
            { msg: 'filename must not contain ".."' },
          ],
        },
      },
    };
    expect(fastApiErrorMessage(error, 'fallback')).toBe(
      'field required; filename must not contain ".."'
    );
  });

  it('gives a helpful message when the Python service is unreachable', () => {
    const error = { code: 'ECONNREFUSED' };
    expect(fastApiErrorMessage(error, 'fallback')).toMatch(/uvicorn src\.api:app/);
  });

  it('falls back to error.message when there is no response body', () => {
    const error = { message: 'timeout of 120000ms exceeded' };
    expect(fastApiErrorMessage(error, 'fallback')).toBe('timeout of 120000ms exceeded');
  });

  it('falls back to the provided default when nothing else is available', () => {
    const error = {};
    expect(fastApiErrorMessage(error, 'Failed to process question')).toBe(
      'Failed to process question'
    );
  });
});
