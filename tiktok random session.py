import os
import binascii
from multiprocessing import Process, Value, Lock

def generate_codes_batch(batch_size, total_counter, lock):
    while True:
        # Hızlı batch üretim
        codes = [binascii.hexlify(os.urandom(16)).decode() for _ in range(batch_size)]
        
        # Dosyaya yazma (kilit ile thread-safe)
        with lock:
            with open("session.txt", "a") as f:
                f.write("\n".join(codes) + "\n")
            total_counter.value += batch_size
            print(f"Toplam üretilen kod sayısı: {total_counter.value}", end='\r')

if __name__ == "__main__":
    batch_size = 10000     # her işlem için batch boyutu
    num_processes = os.cpu_count()  # CPU çekirdeği kadar process
    
    total_counter = Value('i', 0)  # paylaşılan toplam sayaç
    lock = Lock()                  # dosya yazımı için kilit

    processes = []
    for _ in range(num_processes):
        p = Process(target=generate_codes_batch, args=(batch_size, total_counter, lock))
        p.start()
        processes.append(p)
    
    for p in processes:
        p.join()