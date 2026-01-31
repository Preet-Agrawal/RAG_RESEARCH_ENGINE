import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import { join } from 'path';

const execAsync = promisify(exec);

interface CompareRequest {
  question: string;
  filename: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: CompareRequest = await request.json();
    const { question, filename } = body;

    if (!question || !filename) {
      return NextResponse.json(
        { error: 'Question and filename are required' },
        { status: 400 }
      );
    }

    const pythonScript = join(process.cwd(), '..', 'process_pdf.py');
    const uploadsDir = join(process.cwd(), '..', 'data', 'uploads');
    const filepath = join(uploadsDir, filename);

    const escapedQuestion = question.replace(/"/g, '\\"').replace(/`/g, '\\`');
    const command = `python3 "${pythonScript}" "${filepath}" "compare" "${escapedQuestion}"`;

    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: 300000, // 5 minute timeout for comparison
        maxBuffer: 1024 * 1024 * 10,
      });

      if (stderr) {
        console.error('Python stderr:', stderr);
      }

      const response = JSON.parse(stdout);

      if (response.error) {
        return NextResponse.json(
          { success: false, error: response.error },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        question: response.question,
        comparison: response.comparison,
        bestStrategy: response.best_strategy,
        totalLatency: response.total_latency,
      });
    } catch (error: any) {
      console.error('Execution error:', error);

      if (error.killed) {
        return NextResponse.json(
          { success: false, error: 'Request timed out. The document may be too large for comparison.' },
          { status: 504 }
        );
      }

      return NextResponse.json(
        { success: false, error: 'Failed to compare strategies', details: error.message },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Request error:', error);
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
