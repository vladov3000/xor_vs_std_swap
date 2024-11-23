#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <utility>

#ifndef SWAP_FUNCTION
#error "SWAP_FUNCTION must be defined to be std::swap or xor_swap"
#endif

/*
 * This code needs to be inline assembly, otherwise it is optimized away.
 * { x = y ^ x; y = x ^ y; x = y ^ x; }
 */

#define xor_swap(x, y) \
  { asm("eor %0, %1, %0; eor %1, %0, %1; eor %0, %1, %0;" : "+Kr" (x), "+Kr" (y)); }

int main(int argc, char** argv) {
  assert(argc == 2);

  char* end_pointer  = NULL;
  long  number_count = strtoll(argv[1], &end_pointer, 10);
  assert(errno == 0);
  assert(end_pointer != NULL && *end_pointer == 0);
  assert(number_count > 0);

  size_t numbers_size = number_count * sizeof(int);
  int    protection   = PROT_READ | PROT_WRITE;
  int    flags        = MAP_PRIVATE | MAP_ANON;
  int*   numbers      = (int*) mmap(NULL, numbers_size, protection, flags, -1, 0);
  
  int fd = open("/dev/urandom", O_RDONLY);
  assert(fd != -1);
  
  ssize_t bytes_read = read(fd, numbers, numbers_size);
  assert(bytes_read == numbers_size);

  uint64_t start_time = clock_gettime_nsec_np(CLOCK_PROCESS_CPUTIME_ID);

  bool swapped = true;
  int  end     = number_count;
  while (swapped) {
    swapped = false;
    for (size_t i = 1; i < end; i++) {
      int previous = numbers[i - 1];
      int current  = numbers[i];
      if (previous > current) {
	SWAP_FUNCTION(previous, current);
	numbers[i - 1] = previous;
	numbers[i]     = current;
	swapped        = true;
      }
    }
    end = end - 1;
  }

  uint64_t end_time = clock_gettime_nsec_np(CLOCK_PROCESS_CPUTIME_ID);
  printf("%lld\n", end_time - start_time);

#ifdef VERIFY
  bool sorted = true;
  for (int i = 1; i < number_count; i++) {
    if (numbers[i - 1] > numbers[i]) {
      sorted = false;
      break;
    }
  }
  assert(sorted);
#endif
}
