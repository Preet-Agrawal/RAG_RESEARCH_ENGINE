import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import { join } from 'path';

const execAsync = promisify(exec);

export type Strategy =
  | 'combined'
  | 'baseline'
  | 'attention_anchoring'
  | 'relevance_restructuring'
  | 'query_aware_compression'
  | 'chunked_reading';

interface AskRequest {
  question: string;
  filename: string;
  strategy?: Strategy;
}

interface ProcessResponse {
  answer: string;
  sources: string[];
  confidence: number;
  strategy_used: string;
  chunks_processed: number;
  latency: number;
  strategy_explanation: string;
  error?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: AskRequest = await request.json();
    const { question, filename, strategy = 'combined' } = body;

    if (!question || !filename) {
      return NextResponse.json(
        { error: 'Question and filename are required' },
        { status: 400 }
      );
    }

    // Validate strategy
    const validStrategies: Strategy[] = [
      'combined',
      'baseline',
      'attention_anchoring',
      'relevance_restructuring',
      'query_aware_compression',
      'chunked_reading'
    ];

    if (!validStrategies.includes(strategy)) {
      return NextResponse.json(
        { error: `Invalid strategy. Valid options: ${validStrategies.join(', ')}` },
        { status: 400 }
      );
    }

    // Path to the Python script that processes PDF with middle-recovery strategies
    const pythonScript = join(process.cwd(), '..', 'process_pdf.py');
    const uploadsDir = join(process.cwd(), '..', 'data', 'uploads');
    const filepath = join(uploadsDir, filename);

    // Execute Python script with action, question, and strategy parameters
    const escapedQuestion = question.replace(/"/g, '\\"').replace(/`/g, '\\`');
    const command = `python3 "${pythonScript}" "${filepath}" "ask" "${escapedQuestion}" "${strategy}"`;

    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: 120000, // 2 minute timeout for chunked reading strategy
        maxBuffer: 1024 * 1024 * 10, // 10MB buffer
      });

      if (stderr) {
        console.error('Python stderr:', stderr);
      }

      // Parse the response from Python
      const response: ProcessResponse = JSON.parse(stdout);

      if (response.error) {
        return NextResponse.json(
          {
            success: false,
            error: response.error,
          },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        answer: response.answer,
        sources: response.sources || [],
        confidence: response.confidence || 0,
        strategyUsed: response.strategy_used,
        chunksProcessed: response.chunks_processed,
        latency: response.latency,
        strategyExplanation: response.strategy_explanation,
      });
    } catch (error: any) {
      console.error('Execution error:', error);

      // Check if it's a timeout error
      if (error.killed) {
        return NextResponse.json(
          {
            success: false,
            error: 'Request timed out. The document may be too large.',
          },
          { status: 504 }
        );
      }

      return NextResponse.json(
        {
          success: false,
          error: 'Failed to process question',
          details: error.message,
        },
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
