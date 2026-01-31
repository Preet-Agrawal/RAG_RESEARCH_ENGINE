import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import { join } from 'path';

const execAsync = promisify(exec);

interface BenchmarkRequest {
  filename: string;
  needleFact?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: BenchmarkRequest = await request.json();
    const { filename, needleFact } = body;

    if (!filename) {
      return NextResponse.json(
        { error: 'Filename is required' },
        { status: 400 }
      );
    }

    const pythonScript = join(process.cwd(), '..', 'process_pdf.py');
    const uploadsDir = join(process.cwd(), '..', 'data', 'uploads');
    const filepath = join(uploadsDir, filename);

    let command = `python3 "${pythonScript}" "${filepath}" "benchmark"`;
    if (needleFact) {
      const escapedNeedle = needleFact.replace(/"/g, '\\"').replace(/`/g, '\\`');
      command += ` "${escapedNeedle}"`;
    }

    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: 600000, // 10 minute timeout for benchmark
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

      // Transform snake_case to camelCase for frontend
      return NextResponse.json({
        success: true,
        needleFact: response.needle_fact,
        testPositions: response.test_positions,
        results: response.results.map((r: any) => ({
          positionPercent: r.position_percent,
          positionZone: r.position_zone,
          baselineFound: r.baseline_found,
          baselineConfidence: r.baseline_confidence,
          combinedFound: r.combined_found,
          combinedConfidence: r.combined_confidence,
          recoverySuccess: r.recovery_success,
        })),
        summary: {
          baselineAccuracy: response.summary.baseline_accuracy,
          combinedAccuracy: response.summary.combined_accuracy,
          improvement: response.summary.improvement,
          deadZonePositions: response.summary.dead_zone_positions,
          deadZoneRecoveryRate: response.summary.dead_zone_recovery_rate,
        },
        totalLatency: response.total_latency,
      });
    } catch (error: any) {
      console.error('Execution error:', error);

      if (error.killed) {
        return NextResponse.json(
          { success: false, error: 'Benchmark timed out. This test runs multiple queries and may take several minutes.' },
          { status: 504 }
        );
      }

      return NextResponse.json(
        { success: false, error: 'Failed to run benchmark', details: error.message },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Request error:', error);
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
