"""
================================================================================
CSC-334: Distributed Task Offloading & Remote Compute System
Sample Complex Project Task: Multi-Stage Scientific & Algorithmic Simulation
Student Name: Muhammad Ahmad Mujtaba (FA23-BSE-041)
================================================================================
"""

import sys
import time
import math
import random
import json
import os


def report_progress(percent: float, message: str):
    """Prints standardized progress string for the server daemon to intercept and stream."""
    print(f"[PROGRESS] {percent:.1f}% - {message}", flush=True)


def stage1_monte_carlo_pi(num_samples: int = 2_000_000):
    report_progress(10.0, f"Stage 1: Monte Carlo Pi Simulation ({num_samples:,} iterations)...")
    inside = 0
    step = num_samples // 10
    
    for i in range(num_samples):
        x = random.random()
        y = random.random()
        if x * x + y * y <= 1.0:
            inside += 1
            
        if (i + 1) % step == 0:
            batch = (i + 1) // step
            pct = 10.0 + (batch / 10.0) * 35.0  # 10% to 45%
            report_progress(pct, f"Monte Carlo sample batch {batch}/10 ({i+1:,} points processed)")

    pi_approx = 4.0 * (inside / num_samples)
    err = abs(pi_approx - math.pi)
    report_progress(45.0, f"Stage 1 Complete: Pi ~ {pi_approx:.6f} (Absolute Error: {err:.6f})")
    return {"pi_estimate": pi_approx, "error": err, "samples": num_samples}


def stage2_matrix_operations(dim: int = 700):
    report_progress(50.0, f"Stage 2: Heavy Matrix Factorization & Tensor Dot Products ({dim}x{dim})...")
    
    try:
        import numpy as np
        report_progress(55.0, "Allocating random floating-point matrices on Server memory...")
        A = np.random.randn(dim, dim).astype(np.float64)
        B = np.random.randn(dim, dim).astype(np.float64)
        
        report_progress(70.0, "Computing dense matrix-matrix multiplication on Server CPU cores...")
        C = np.dot(A, B)
        
        report_progress(82.0, "Computing Frobenius norm and matrix trace...")
        f_norm = float(np.linalg.norm(C))
        m_trace = float(np.trace(C))
        
        report_progress(88.0, "Computing eigenvalues of sub-tensor...")
        sub_eig = np.linalg.eigvals(C[:80, :80])
        max_eig = float(np.max(np.real(sub_eig)))
        
        metrics = {
            "engine": "NumPy OpenBLAS Multi-Threaded",
            "dimensions": f"{dim}x{dim}",
            "frobenius_norm": f_norm,
            "matrix_trace": m_trace,
            "max_real_eigenvalue": max_eig
        }
    except Exception as e:
        report_progress(75.0, f"NumPy unavailable, running pure python mathematical iterations...")
        acc = 0.0
        for i in range(120_000):
            acc += math.sqrt(i) * math.cos(i)
        metrics = {"engine": "Python Math Fallback", "iterations": 120_000, "result": acc}

    report_progress(92.0, "Stage 2 Complete: Numerical linear algebra operations finished.")
    return metrics


def stage3_prime_search(search_limit: int = 60_000):
    report_progress(93.0, f"Stage 3: Prime Sieve & Number-Theoretic Search (Limit: {search_limit:,})...")
    is_prime = [True] * (search_limit + 1)
    is_prime[0] = is_prime[1] = False
    
    for p in range(2, int(math.isqrt(search_limit)) + 1):
        if is_prime[p]:
            for multiple in range(p * p, search_limit + 1, p):
                is_prime[multiple] = False
                
    prime_count = sum(is_prime)
    report_progress(98.0, f"Stage 3 Complete: Found {prime_count:,} primes up to {search_limit:,}")
    return {"search_limit": search_limit, "primes_found": prime_count}


def main():
    print("=" * 70)
    print("  CSC-334: REMOTE WORKER COMPLEX PROJECT EXECUTION PIPELINE")
    print("=" * 70)
    print(f"[*] Process ID (PID) : {os.getpid()}")
    print(f"[*] Python Executable : {sys.executable}")
    t_start = time.time()
    
    report_progress(5.0, "Initializing project execution environment on worker node...")
    time.sleep(0.4)
    
    # Run the three computational stages
    mc_results = stage1_monte_carlo_pi(num_samples=1_500_000)
    matrix_results = stage2_matrix_operations(dim=650)
    prime_results = stage3_prime_search(search_limit=70_000)
    
    total_duration = time.time() - t_start
    report_progress(100.0, f"All project stages executed successfully in {total_duration:.2f}s!")
    
    final_output = {
        "status": "SUCCESS",
        "task_name": "Complex Multi-Stage Scientific Simulation",
        "author": "Muhammad Ahmad Mujtaba (FA23-BSE-041)",
        "total_runtime_seconds": round(total_duration, 3),
        "stage1_monte_carlo": mc_results,
        "stage2_matrix_algebra": matrix_results,
        "stage3_prime_search": prime_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print("\n[FINAL EXECUTION SUMMARY RESULT]")
    print(json.dumps(final_output, indent=2))
    
    # Save output artifact if destination path is passed in sys.argv
    if len(sys.argv) > 1 and sys.argv[1]:
        output_file = sys.argv[1]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2)
        print(f"\n[ARTIFACT] Result JSON persisted to: {output_file}")


if __name__ == "__main__":
    main()
