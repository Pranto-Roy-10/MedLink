"""
Elliptic Curve Cryptography Implementation
Implements point arithmetic on elliptic curves for ECDSA and key exchange.

Mathematical Foundation:
Elliptic Curve: y² = x³ + ax + b (mod p)
Point at Infinity: O (additive identity)
Point Addition: P + Q = R
Point Doubling: P + P = 2P
Scalar Multiplication: kP = P + P + ... + P (k times)
"""


class Point:
    """Represents a point on an elliptic curve."""
    
    def __init__(self, x, y, curve):
        """
        Initialize an elliptic curve point.
        
        Args:
            x: X-coordinate (None for point at infinity)
            y: Y-coordinate (None for point at infinity)
            curve: EllipticCurve object this point belongs to
        """
        self.x = x
        self.y = y
        self.curve = curve
        
        # Validate point is on curve (unless point at infinity)
        if x is not None and y is not None:
            if not self.is_on_curve():
                raise ValueError(f"Point ({x}, {y}) is not on the curve")
    
    def is_at_infinity(self):
        """Check if this is the point at infinity."""
        return self.x is None and self.y is None
    
    def is_on_curve(self):
        """
        Verify point is on elliptic curve.
        
        Formula: y² ≡ x³ + ax + b (mod p)
        
        Returns:
            bool: True if point satisfies the curve equation
        """
        if self.is_at_infinity():
            return True
        
        left = (self.y ** 2) % self.curve.p
        right = (self.x ** 3 + self.curve.a * self.x + self.curve.b) % self.curve.p
        return left == right
    
    def __eq__(self, other):
        """Check if two points are equal."""
        if self.is_at_infinity() and other.is_at_infinity():
            return True
        return self.x == other.x and self.y == other.y
    
    def __repr__(self):
        if self.is_at_infinity():
            return "O"
        return f"({self.x}, {self.y})"


class EllipticCurve:
    """
    Represents an elliptic curve over a finite field.
    
    Curve equation: y² ≡ x³ + ax + b (mod p)
    """
    
    def __init__(self, a, b, p):
        """
        Initialize elliptic curve.
        
        Mathematical Requirements:
        - 4a³ + 27b² ≢ 0 (mod p) [discriminant must be non-zero]
        - p must be prime
        
        Args:
            a: Coefficient a in y² = x³ + ax + b
            b: Coefficient b in y² = x³ + ax + b
            p: Prime modulus (field size)
        """
        self.a = a
        self.b = b
        self.p = p
        
        # Check discriminant
        discriminant = (4 * a ** 3 + 27 * b ** 2) % p
        if discriminant == 0:
            raise ValueError("Curve is singular (discriminant = 0)")
    
    def point_at_infinity(self):
        """Return the point at infinity (identity element)."""
        return Point(None, None, self)
    
    def point_addition(self, P, Q):
        """
        Add two points on the elliptic curve.
        
        Mathematical Formula:
        Case 1: P = O → P + Q = Q
        Case 2: Q = O → P + Q = P
        Case 3: P = (x, y), Q = (x, -y) → P + Q = O (inverse)
        Case 4: P = Q → Use point doubling
        Case 5: P ≠ Q → General addition
        
        For Case 5 (P ≠ Q):
        - λ = (yQ - yP) / (xQ - xP) mod p [slope of line through P and Q]
        - xR = λ² - xP - xQ mod p
        - yR = λ(xP - xR) - yP mod p
        - R = (xR, yR)
        
        Args:
            P: First point
            Q: Second point
        
        Returns:
            Point: P + Q
        """
        # Case 1: P is point at infinity
        if P.is_at_infinity():
            return Q
        
        # Case 2: Q is point at infinity
        if Q.is_at_infinity():
            return P
        
        # Case 3: P = -Q (additive inverse)
        if P.x == Q.x:
            if (P.y + Q.y) % self.p == 0:
                return self.point_at_infinity()
            # If P.x == Q.x and P.y == Q.y, use doubling
        
        # Case 4: P = Q → Point doubling
        if P == Q:
            return self.point_doubling(P)
        
        # Case 5: General addition (P ≠ Q)
        # Calculate slope: λ = (yQ - yP) / (xQ - xP) mod p
        numerator = (Q.y - P.y) % self.p
        denominator = (Q.x - P.x) % self.p
        
        # Modular inverse: denominator^(-1) mod p
        lambda_coeff = (numerator * pow(denominator, -1, self.p)) % self.p
        
        # Calculate result coordinates
        x_r = (lambda_coeff ** 2 - P.x - Q.x) % self.p
        y_r = (lambda_coeff * (P.x - x_r) - P.y) % self.p
        
        return Point(x_r, y_r, self)
    
    def point_doubling(self, P):
        """
        Double a point on the elliptic curve (P + P = 2P).
        
        Mathematical Formula:
        For P = (x, y) where y ≠ 0:
        - λ = (3x² + a) / (2y) mod p [derivative slope]
        - xR = λ² - 2x mod p
        - yR = λ(x - xR) - y mod p
        - 2P = (xR, yR)
        
        Special case: If y = 0, then 2P = O (point at infinity)
        
        Args:
            P: Point to double
        
        Returns:
            Point: 2P
        """
        # Check if P is at infinity
        if P.is_at_infinity():
            return self.point_at_infinity()
        
        # If y-coordinate is 0, result is point at infinity
        if P.y == 0:
            return self.point_at_infinity()
        
        # Calculate slope: λ = (3x² + a) / (2y) mod p
        numerator = (3 * P.x ** 2 + self.a) % self.p
        denominator = (2 * P.y) % self.p
        
        # Modular inverse
        lambda_coeff = (numerator * pow(denominator, -1, self.p)) % self.p
        
        # Calculate result coordinates
        x_r = (lambda_coeff ** 2 - 2 * P.x) % self.p
        y_r = (lambda_coeff * (P.x - x_r) - P.y) % self.p
        
        return Point(x_r, y_r, self)
    
    def scalar_multiplication(self, k, P):
        """
        Multiply a point by a scalar: k·P = P + P + ... + P (k times)
        
        Uses Double-and-Add Algorithm for efficiency:
        1. Convert k to binary: k = Σ(bi·2^i) where bi ∈ {0,1}
        2. Result = Σ(bi·2^i·P) = Σ(bi·(P doubled i times))
        3. Complexity: O(log k) instead of O(k)
        
        Algorithm Steps:
        - Start with R = O (point at infinity)
        - For each bit of k from least significant to most significant:
          - If bit is 1, add current P to result
          - Double P for next iteration
        
        Args:
            k: Scalar (integer)
            P: Point to multiply
        
        Returns:
            Point: k·P
        """
        if k == 0:
            return self.point_at_infinity()
        
        if k < 0:
            raise ValueError("Scalar must be non-negative")
        
        # Double-and-add algorithm
        result = self.point_at_infinity()
        addend = P
        
        while k:
            if k & 1:  # If least significant bit is 1
                result = self.point_addition(result, addend)
            addend = self.point_doubling(addend)
            k >>= 1  # Right shift by 1 (divide by 2)
        
        return result


# Standard curve parameters (secp256k1-like, for demonstration)
# In production, use secp256r1 or secp256k1
def create_curve_secp256k1_demo():
    """
    Create a demo elliptic curve similar to secp256k1.
    
    Parameters:
    a = 0 (simplified)
    b = 7
    p = 2^256 - 2^32 - 977 (large prime)
    
    Curve: y² = x³ + 7 (mod p)
    """
    a = 0
    b = 7
    p = 2**256 - 2**32 - 977
    return EllipticCurve(a, b, p)


def create_test_curve():
    """
    Create a simple test elliptic curve for demonstration.
    
    Parameters:
    a = 1, b = 1, p = 1009 (small prime for testing)
    Curve: y² = x³ + x + 1 (mod 1009)
    """
    return EllipticCurve(a=1, b=1, p=1009)
