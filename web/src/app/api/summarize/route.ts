import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import { join } from 'path';

const execAsync = promisify(exec);

interface SummarizeRequest {
  filename: string;
}

interface ChunkSummary {
  chunk_id: number;
  total_chunks: number;
  zone: 'beginning' | 'middle' | 'end';
  position: number;
  summary: string;
  is_middle: boolean;
}

interface SummarizeResponse {
  success: boolean;
  total_chunks: number;
  chunk_summaries: ChunkSummary[];
  overall_summary: string;
  middle_chunks_count: number;
  latency: number;
  error?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: SummarizeRequest = await request.json();
    const { filename } = body;

    if (!filename) {
      return NextResponse.json(
        { error: 'Filename is required' },
        { status: 400 }
      );
    }

    const pythonScript = join(process.cwd(), '..', 'process_pdf.py');
    const uploadsDir = join(process.cwd(), '..', 'data', 'uploads');
    const filepath = join(uploadsDir, filename);

    const command = `python3 "${pythonScript}" "${filepath}" "summarize"`;

    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: 180000, // 3 minute timeout for summarization
        maxBuffer: 1024 * 1024 * 10,
      });

      if (stderr) {
        console.error('Python stderr:', stderr);
      }

      const response: SummarizeResponse = JSON.parse(stdout);

      if (!response.success) {
        return NextResponse.json(
          { success: false, error: response.error },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        totalChunks: response.total_chunks,
        chunkSummaries: response.chunk_summaries.map(chunk => ({
          chunkId: chunk.chunk_id,
          totalChunks: chunk.total_chunks,
          zone: chunk.zone,
          position: chunk.position,
          summary: chunk.summary,
          isMiddle: chunk.is_middle,
        })),
        overallSummary: response.overall_summary,
        middleChunksCount: response.middle_chunks_count,
        latency: response.latency,
      });
    } catch (error: any) {
      console.error('Execution error:', error);

      if (error.killed) {
        return NextResponse.json(
          { success: false, error: 'Request timed out. The document may be too large.' },
          { status: 504 }
        );
      }

      return NextResponse.json(
        { success: false, error: 'Failed to summarize document', details: error.message },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Request error:', error);
    return NextResponse.json(
      { error: 'Invalid request' },
      { status: 400 }
    );
  }
}
