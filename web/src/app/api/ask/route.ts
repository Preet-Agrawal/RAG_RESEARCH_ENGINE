import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import { join } from 'path';

const execAsync = promisify(exec);

interface AskRequest {
  question: string;
  filename: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: AskRequest = await request.json();
    const { question, filename } = body;

    if (!question || !filename) {
      return NextResponse.json(
        { error: 'Question and filename are required' },
        { status: 400 }
      );
    }

    // Path to the Python script that will process the PDF and answer questions
    const pythonScript = join(process.cwd(), '..', 'process_pdf.py');
    const uploadsDir = join(process.cwd(), '..', 'data', 'uploads');
    const filepath = join(uploadsDir, filename);

    // Execute Python script to process the PDF and answer the question
    // This is a simplified version - you'll need to create the Python script
    const command = `python3 "${pythonScript}" "${filepath}" "${question.replace(/"/g, '\\"')}"`;

    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: 60000, // 60 second timeout
      });

      if (stderr) {
        console.error('Python error:', stderr);
      }

      // Parse the response from Python
      const response = JSON.parse(stdout);

      return NextResponse.json({
        success: true,
        answer: response.answer,
        sources: response.sources || [],
        confidence: response.confidence || 0,
        positions: response.positions || [],
      });
    } catch (error: any) {
      console.error('Execution error:', error);
      return NextResponse.json(
        {
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
