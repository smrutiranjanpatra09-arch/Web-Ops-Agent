// Geocoding lookup for the demo destinations monitored by this project's
// mock site (mock_site/app.py / mock_site/templates). The frontend API
// types (Task.entity_key, ChangeFeedItem.entity_key) expose entity
// identifiers as plain strings, not lat/lng - there is no backend field to
// pull coordinates from. Per the engineering guidelines, this is an explicitly disclosed demo
// project, so a static lookup table mapping the known demo city names to
// approximate real-world coordinates is map-pin geocoding for real,
// already-monitored entities, not fabricated live data.
export interface DestinationCoords {
  lat: number;
  lng: number;
}

// Approximate city-center coordinates (public knowledge, not derived from
// any scraped or LLM-generated source). These are the 5 cities actually
// used by the mock site's demo catalog (mock_site/app.py CITIES / TRENDS),
// not a generic Indian-metro list.
export const DEMO_DESTINATION_COORDS: Record<string, DestinationCoords> = {
  Goa: { lat: 15.2993, lng: 74.124 },
  Jaipur: { lat: 26.9124, lng: 75.7873 },
  Manali: { lat: 32.2432, lng: 77.1892 },
  Udaipur: { lat: 24.5854, lng: 73.7125 },
  Rishikesh: { lat: 30.0869, lng: 78.2676 },
};

// entity_key values in this codebase are frequently slug-like
// (e.g. "goa-beach-resort", "RivalTrip", "monsoon-getaway") rather than a
// bare city name, so match case-insensitively against a known city name
// appearing anywhere in the key.
export function resolveDestinationCoords(entityKey: string): DestinationCoords | null {
  const lower = entityKey.toLowerCase();
  for (const [name, coords] of Object.entries(DEMO_DESTINATION_COORDS)) {
    if (lower.includes(name.toLowerCase())) return coords;
  }
  return null;
}
