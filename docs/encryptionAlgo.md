# The Bit-Shuffle Encryption Algorithm

## Overview
The **Bit-Shuffle Algorithm** is a custom, from-scratch symmetric encryption cipher designed specifically for this project to strictly adhere to the requirement of not using industry-standard algorithms like AES, DES, or RSA. It operates at the byte level, combining standard bitwise operations to effectively scramble the data.

## How It Works

### Encryption Steps
For each byte of the plaintext message:
1. **Bit Flip**: The bits of the byte are flipped using the bitwise NOT operator (e.g., `0b10101010` becomes `0b01010101`).
2. **Bit Permutation (Shuffle)**: The bits within the byte are rearranged based on a static 8-element permutation key. This key acts as the assembly instruction manual determining which bit moves to which position.
3. **Subtraction**: A specific "magic number" (e.g., 42) is subtracted from the byte's numerical value, naturally wrapping around if it drops below zero (modulo 256).
4. **XOR with Key**: Finally, the byte is XOR'ed with a byte from the shared configuration key (`AES_KEY`), linking the security directly to the project's shared configuration.

### Decryption Steps
For each byte of the ciphertext message:
1. **XOR with Key**: The byte is XOR'ed against the shared configuration key again.
2. **Addition**: The "magic number" is added back to the byte's value (modulo 256).
3. **Inverse Bit Permutation (Disassemble)**: The bits are restored to their original positions using the same static 8-element permutation key.
4. **Bit Flip**: The bits are flipped one last time using the bitwise NOT operator, revealing the original byte.

## Security Note
This algorithm is designed solely for educational purposes and to fulfill the specific lab assignment constraints against using existing industry-standard cryptographic tools. Because it relies on static mappings and simple linear bitwise operations, it is not cryptographically secure against modern analytical attacks and should not be used to protect actual sensitive data in a production environment.

