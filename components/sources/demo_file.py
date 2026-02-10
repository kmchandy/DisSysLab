# components/sources/demo_file.py

"""
Demo File Source - Read sample CSV/JSON files for learning

This demo version uses pre-loaded sample data so students can learn
file processing without needing actual files. Perfect for teaching!

Compare with file_source.py to see the demo → real pattern.
"""

import json
import csv
from io import StringIO


class DemoFileSource:
    """
    Demo file source with built-in sample data.

    No setup needed - works immediately with realistic sample data.

    Args:
        filename: "customers" or "events" (built-in samples)
        format: "csv" or "json"

    Returns:
        Dict for each row/item

    Example:
        >>> from components.sources.demo_file import DemoFileSource
        >>> source = DemoFileSource(filename="customers", format="csv")
        >>> while True:
        ...     customer = source.run()
        ...     if customer is None:
        ...         break
        ...     print(customer["name"])
    """

    # Embedded sample data
    SAMPLE_CUSTOMERS_CSV = """id,name,email,age,city,status
1,Alice Johnson,alice.johnson@email.com,28,New York,active
2,Bob Smith,bob.smith@email.com,34,San Francisco,active
3,Carol White,carol.white@email.com,45,Chicago,inactive
4,David Brown,david.brown@email.com,31,Boston,active
5,Emma Davis,emma.davis@email.com,26,Seattle,active
6,Frank Miller,frank.miller@email.com,52,Miami,inactive
7,Grace Wilson,grace.wilson@email.com,29,Denver,active
8,Henry Moore,henry.moore@email.com,38,Austin,active
9,Iris Taylor,iris.taylor@email.com,41,Portland,inactive
10,Jack Anderson,jack.anderson@email.com,33,Atlanta,active
11,Kate Thomas,kate.thomas@email.com,27,Nashville,active
12,Leo Jackson,leo.jackson@email.com,49,Phoenix,inactive
13,Mary Martin,mary.martin@email.com,35,Dallas,active
14,Nathan Lee,nathan.lee@email.com,30,Houston,active
15,Olivia Harris,olivia.harris@email.com,44,Philadelphia,inactive
16,Paul Clark,paul.clark@email.com,32,San Diego,active
17,Quinn Lewis,quinn.lewis@email.com,28,Detroit,active
18,Rachel Walker,rachel.walker@email.com,36,Minneapolis,inactive
19,Steve Hall,steve.hall@email.com,40,Tampa,active
20,Tina Allen,tina.allen@email.com,25,Charlotte,active
21,Uma Young,uma.young@email.com,47,Indianapolis,inactive
22,Victor King,victor.king@email.com,31,Columbus,active
23,Wendy Wright,wendy.wright@email.com,29,San Jose,active
24,Xavier Lopez,xavier.lopez@email.com,53,Jacksonville,inactive
25,Yara Hill,yara.hill@email.com,33,Fort Worth,active
26,Zane Scott,zane.scott@email.com,37,Austin,active
27,Amy Green,amy.green@email.com,42,Seattle,inactive
28,Brian Adams,brian.adams@email.com,30,Denver,active
29,Cathy Baker,cathy.baker@email.com,26,Portland,active
30,Dan Nelson,dan.nelson@email.com,48,Chicago,inactive
31,Ella Carter,ella.carter@email.com,34,Boston,active
32,Fred Mitchell,fred.mitchell@email.com,29,Miami,active
33,Gina Perez,gina.perez@email.com,39,New York,inactive
34,Hugo Roberts,hugo.roberts@email.com,31,San Francisco,active
35,Ivy Turner,ivy.turner@email.com,27,Los Angeles,active
36,Jake Phillips,jake.phillips@email.com,45,Phoenix,inactive
37,Kim Campbell,kim.campbell@email.com,32,Dallas,active
38,Luke Parker,luke.parker@email.com,28,Houston,active
39,Mia Evans,mia.evans@email.com,50,Philadelphia,inactive
40,Nick Edwards,nick.edwards@email.com,35,San Diego,active
41,Opal Collins,opal.collins@email.com,29,Detroit,active
42,Pete Stewart,pete.stewart@email.com,41,Minneapolis,inactive
43,Rose Sanchez,rose.sanchez@email.com,33,Tampa,active
44,Sam Morris,sam.morris@email.com,26,Charlotte,active
45,Tara Rogers,tara.rogers@email.com,46,Indianapolis,inactive
46,Ursula Reed,ursula.reed@email.com,30,Columbus,active
47,Vince Cook,vince.cook@email.com,28,San Jose,active
48,Wanda Morgan,wanda.morgan@email.com,52,Jacksonville,inactive
49,Xander Bell,xander.bell@email.com,34,Fort Worth,active
50,Yvonne Murphy,yvonne.murphy@email.com,31,Austin,active"""

    SAMPLE_EVENTS_JSON = [
        {"id": 1, "type": "login", "user_id": 42, "timestamp": "2026-02-08T10:30:00Z",
            "ip_address": "192.168.1.100", "success": True},
        {"id": 2, "type": "page_view", "user_id": 15, "timestamp": "2026-02-08T10:31:15Z",
            "page": "/products", "duration_seconds": 45},
        {"id": 3, "type": "purchase", "user_id": 28, "timestamp": "2026-02-08T10:32:20Z",
            "amount": 99.99, "product_id": "PROD-123"},
        {"id": 4, "type": "login", "user_id": 7, "timestamp": "2026-02-08T10:33:00Z",
            "ip_address": "10.0.0.50", "success": False},
        {"id": 5, "type": "page_view", "user_id": 42, "timestamp": "2026-02-08T10:34:10Z",
            "page": "/checkout", "duration_seconds": 120},
        {"id": 6, "type": "logout", "user_id": 15,
            "timestamp": "2026-02-08T10:35:00Z", "session_duration": 1800},
        {"id": 7, "type": "error", "user_id": 28, "timestamp": "2026-02-08T10:36:45Z",
            "error_code": "E404", "message": "Page not found"},
        {"id": 8, "type": "purchase", "user_id": 42, "timestamp": "2026-02-08T10:37:30Z",
            "amount": 149.50, "product_id": "PROD-456"},
        {"id": 9, "type": "login", "user_id": 33, "timestamp": "2026-02-08T10:38:00Z",
            "ip_address": "192.168.1.200", "success": True},
        {"id": 10, "type": "page_view", "user_id": 7,
            "timestamp": "2026-02-08T10:39:15Z", "page": "/about", "duration_seconds": 30},
        {"id": 11, "type": "purchase", "user_id": 33, "timestamp": "2026-02-08T10:40:00Z",
            "amount": 299.00, "product_id": "PROD-789"},
        {"id": 12, "type": "login", "user_id": 88, "timestamp": "2026-02-08T10:41:30Z",
            "ip_address": "172.16.0.10", "success": True},
        {"id": 13, "type": "page_view", "user_id": 28, "timestamp": "2026-02-08T10:42:00Z",
            "page": "/products", "duration_seconds": 90},
        {"id": 14, "type": "logout", "user_id": 42,
            "timestamp": "2026-02-08T10:43:15Z", "session_duration": 2400},
        {"id": 15, "type": "error", "user_id": 7, "timestamp": "2026-02-08T10:44:00Z",
            "error_code": "E500", "message": "Server error"}
    ]

    def __init__(self, filename="customers", format="csv"):
        """
        Initialize demo file source.

        Args:
            filename: "customers" or "events" (built-in samples)
            format: "csv" or "json"
        """
        self.filename = filename
        self.format = format
        self.data = []
        self.n = 0

        # Load appropriate sample data
        if filename == "customers" and format == "csv":
            self._load_csv_data()
        elif filename == "events" and format == "json":
            self.data = self.SAMPLE_EVENTS_JSON.copy()
        else:
            raise ValueError(
                f"Unknown filename/format combination: {filename}/{format}\n"
                f"Available combinations:\n"
                f"  - filename='customers', format='csv'\n"
                f"  - filename='events', format='json'"
            )

        print(
            f"[DemoFileSource] Loaded {len(self.data)} items from '{filename}' ({format})")

    def _load_csv_data(self):
        """Parse CSV data from string."""
        reader = csv.DictReader(StringIO(self.SAMPLE_CUSTOMERS_CSV))
        for row in reader:
            # Convert numeric fields
            row["id"] = int(row["id"])
            row["age"] = int(row["age"])
            self.data.append(row)

    def run(self):
        """
        Returns n-th item.

        Returns None when complete (signals end of stream).
        """
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


# Test when run directly
if __name__ == "__main__":
    print("Demo File Source - Test")
    print("=" * 60)

    # Test CSV
    print("\nTest 1: Customers CSV")
    print("-" * 60)
    source = DemoFileSource(filename="customers", format="csv")
    count = 0
    finished = False
    while not finished:
        customer = source.run()
        if customer and count < 3:
            print(
                f"  {customer['name']} ({customer['age']}) - {customer['status']}")
        count += 1
        finished = customer is None
    print(f"  ... and {count - 4} more customers")

    # Test JSON
    print("\nTest 2: Events JSON")
    print("-" * 60)
    source = DemoFileSource(filename="events", format="json")
    count = 0
    finished = False
    while not finished:
        event = source.run()
        if event and count < 3:
            print(
                f"  Event {event['id']}: {event['type']} by user {event['user_id']}")
        count += 1
        finished = event is None
    print(f"  ... and {count - 4} more events")

    print("\n" + "=" * 60)
    print("✓ Demo File Source works!")
