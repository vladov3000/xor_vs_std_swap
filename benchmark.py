import argparse
import contextlib
import os
import subprocess

import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from tqdm import tqdm

def compile(swap_function: str) -> str:
    arguments = ["-O2", f"-DSWAP_FUNCTION={swap_function}"]
    output    = f"build/{swap_function}"
    subprocess.check_call(["clang++", *arguments, "main.cpp", "-o", output])
    return output

def run(program: str, number_count: int) -> int:
    output = subprocess.check_output([program, str(number_count)])
    return int(output)

def compute_timings(swap_function: str, number_counts: int, trial_count: int) -> np.ndarray:
    cache = Path(f"build/timings_{swap_function}.npy")
    if cache.exists():
        print(f"Found cached results at \"{cache}\".")
        return np.load(cache)

    program = compile(swap_function)
    
    print(f"Running benchmark for {swap_function}.")
    result = np.empty((len(number_counts), trial_count))
    for i in tqdm(range(len(number_counts))):
        for trial in range(trial_count):
            time = run(program, number_counts[i])
            result[i, trial] = time

    np.save(cache, result)
    return result

def main(arguments):
    with contextlib.suppress(FileExistsError):
        os.mkdir("build")

    swap_functions = ["std::swap", "xor_swap"]
    number_counts  = np.arange(10 * 4096, 15 * 4096, 4096)
    trial_count    = 5

    timings = {}
    for swap_function in swap_functions:
        timings[swap_function] = compute_timings(swap_function, number_counts, trial_count)

    if arguments.table:
        print(" Swap Function | Number Count | Timing ")
        print("---------------+--------------+--------")
        for i, number_count in enumerate(number_counts):
            for swap_function in swap_functions:
                trials   = timings[swap_function][i]
                median   = np.median(trials)
                p25, p75 = np.percentile(trials, [25, 75])
                timing   = f"{median}ns (IQR {p25}-{p75})"
                print(f" {swap_function:<13} | {number_count:>12} | {timing:>8}")

    if arguments.plot:
        plt.style.use("Solarize_Light2")
        
        for i, swap_function in enumerate(swap_functions):
            x = number_counts
            y = np.median(timings[swap_function], axis=1)
            plt.scatter(x, y, label=swap_function)

        plt.title("Bubble Sort With Different Swap Functions")
        plt.xlabel("Number Count")
        plt.ylabel("Timing (ns)")
        plt.figtext(0.01, 0.01, f"The median of {trial_count} trials is plotted.")
        plt.legend()
        plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", action="store_true")
    parser.add_argument("--plot", action="store_true")
    
    arguments = parser.parse_args()
    main(arguments)
