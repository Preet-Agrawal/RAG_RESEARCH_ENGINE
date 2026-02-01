import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import { join } from 'path';

const execAsync = promisify(exec);

interface KVRetrievalRequest {
  numPairs?: number;
}

export async function POST(request: NextRequest) {
  try {
    const body: KVRetrievalRequest = await request.json();
    const { numPairs = 75 } = body;

    // We need a dummy file path since the script expects one, but kv_retrieval doesn't use it
    const pythonScript = join(process.cwd(), '..', 'process_pdf.py');
    const dummyPath = join(process.cwd(), '..', 'README.md'); // Use any existing file

    const command = `python3 "${pythonScript}" "${dummyPath}" "kv_retrieval" "${numPairs}"`;

    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: 300000, // 5 minute timeout
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
        task: response.task,
        numPairs: response.num_pairs,
        testPositions: response.test_positions,
        results: response.results,
        summary: response.summary,
        totalLatency: response.total_latency,
        paperReference: response.paper_reference,
      });
    } catch (error: any) {
      console.error('Execution error:', error);

      if (error.killed) {
        return NextResponse.json(
          { success: false, error: 'Key-value retrieval test timed out.' },
          { status: 504 }
        );
      }

      return NextResponse.json(
        { success: false, error: 'Failed to run key-value retrieval test', details: error.message },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Request error:', error);
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
