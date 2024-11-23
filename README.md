## XOR vs std::swap

There is an [old bit twiddling trick](https://en.wikipedia.org/wiki/XOR_swap_algorithm) that uses XOR to swap two integer values. Theoretically, this optimization saves one register, and on older compilers with worse register allocators, a whole stack allocation.

However, is this trick still relevant today? Moden processors make use of [Tomasulo's algorithm](https://en.wikipedia.org/wiki/Tomasulo%27s_algorithm) to rename registers on the fly and avoid stalls from write after read or write after writer hazards.

To test the performance of the xor trick, we use a swap-heavy algorithm like bubble-sort. Unfortunately, `clang` is too smart on my machine and compiles both variants of the code to efficiently use the `stp` ([store pair of registers](https://developer.arm.com/documentation/ddi0602/2024-03/Base-Instructions/STP--Store-Pair-of-Registers-)) instruction. The solution is to write inline assembly for this functionality.

```C
#define xor_swap(x, y) \
  { asm("eor %0, %1, %0; eor %1, %0, %1; eor %0, %1, %0;" : "+Kr" (x), "+Kr" (y)); }
```

Gross. For the uninitiated, `%0` and `%1` refer to the output operands that are specified after the colon. `+Kr (x)` means we want a register ("r") that we can read and write to ("+"), be used with 32-bit logical instructions (`K`), and is where the variable `x` is stored.

Anyways, we can now run the algorithm on different length random number arrays to get a result. For random number generation, we read from `/dev/urandom`. This may be slower than reading a small seed for a [pseudo random number generator (PRNG)](https://en.wikipedia.org/wiki/Pseudorandom_number_generator), but it works.

Below are the results. `std::swap` gets the win by a significant margin even on the relatively small input of 50,000 4-byte integers.

<p align="center">
  <img src="https://github.com/vladov3000/xor_vs_std_swap/blob/master/Result.png" />
</p>

We can disassemble our programs to double check the inline assembly is not messing up a compiler optimization:

```bash
$ clang -S -DSWAP_FUNCTION=std::swap -O2 main.cpp -o std::swap.s
$ clang -S -DSWAP_FUNCTION=xor_swap -O2 main.cpp -o xor_swap.s
$ git diff std::swap.s xor_swap.s
```

The "-S" flag makes clang emit assembly instead of machine code. The relevant diff is below. The lines starting with "+" are lines present in xor_swap, but not in std::swap.s and vice versa for minus.

```diff
...
 	bl	_clock_gettime_nsec_np
@@ -73,35 +73,37 @@ Lloh1:
 	b	LBB0_9
 LBB0_8:                                 ;   in Loop: Header=BB0_9 Depth=1
 	sub	x8, x8, #1
-	tbz	w11, #0, LBB0_15
+	tbz	w12, #0, LBB0_14
 LBB0_9:                                 ; =>This Loop Header: Depth=1
-                                        ;     Child Loop BB0_13 Depth 2
+                                        ;     Child Loop BB0_12 Depth 2
 	cmp	x8, #2
-	csel	x12, x8, x10, hi
+	csel	x11, x8, x10, hi
 	tst	x8, #0xfffffffe
-	b.eq	LBB0_15
+	b.eq	LBB0_14
 ; %bb.10:                               ;   in Loop: Header=BB0_9 Depth=1
-	mov	w11, #0
-	sub	x12, x12, #1
-	ldr	w13, [x19]
-	mov	x14, x9
-	b	LBB0_13
-LBB0_11:                                ;   in Loop: Header=BB0_13 Depth=2
-	stp	w15, w13, [x14, #-4]
-	mov	w11, #1
-LBB0_12:                                ;   in Loop: Header=BB0_13 Depth=2
-	add	x14, x14, #4
-	subs	x12, x12, #1
+	mov	w12, #0
+	sub	x11, x11, #1
+	ldr	w15, [x19]
+	mov	x13, x9
+	b	LBB0_12
+LBB0_11:                                ;   in Loop: Header=BB0_12 Depth=2
+	add	x13, x13, #4
+	mov	x15, x14
+	subs	x11, x11, #1
 	b.eq	LBB0_8
-LBB0_13:                                ;   Parent Loop BB0_9 Depth=1
+LBB0_12:                                ;   Parent Loop BB0_9 Depth=1
                                         ; =>  This Inner Loop Header: Depth=2
-	ldr	w15, [x14]
-	cmp	w13, w15
-	b.gt	LBB0_11
-; %bb.14:                               ;   in Loop: Header=BB0_13 Depth=2
-	mov	x13, x15
-	b	LBB0_12
-LBB0_15:
+	ldr	w14, [x13]
+	cmp	w15, w14
+	b.le	LBB0_11
+; %bb.13:                               ;   in Loop: Header=BB0_12 Depth=2
+	; InlineAsm Start
+	eor	x15, x14, x15	; eor x14, x15, x14; eor x15, x14, x15;
+	; InlineAsm End
+	stp	w15, w14, [x13, #-4]
+	mov	w12, #1
+	b	LBB0_11
+LBB0_14:
 	mov	w0, #12
 	bl	_clock_gettime_nsec_np
...
```

If you look closely, you will see that there are some renamed registers and labels, but they are almost identical programs with one having some extra xor instructions. In fact, the same `stp` instruction is used, just with a different order of operands.

The conclusion is that you should write the simplest code possible and not waste time including these bit twiddling tricks that only serve to confuse the reader. Modern optimizing compilers don't even emit the right assembly for these snippets. Even embedded processors running code compiled with the lowest optimization level use scoreboarding or other methods to abstract over registers, so I doubt these benchmark results would differ much by any architecture or processor made in the last decade.
