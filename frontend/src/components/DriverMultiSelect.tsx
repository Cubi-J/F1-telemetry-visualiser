import React, { useState, useRef, useEffect } from 'react';

export interface DriverOption {
  code: string;
  name: string;
  team: string;
  color: string;
}

interface DriverMultiSelectProps {
  drivers: DriverOption[];
  selectedDrivers: string[];
  onChange: (selected: string[]) => void;
  loading?: boolean;
  disabled?: boolean;
}

export const DriverMultiSelect: React.FC<DriverMultiSelectProps> = ({
  drivers,
  selectedDrivers,
  onChange,
  loading = false,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggleDriver = (code: string) => {
    if (selectedDrivers.includes(code)) {
      onChange(selectedDrivers.filter((c) => c !== code));
    } else {
      onChange([...selectedDrivers, code]);
    }
  };

  const handleSelectAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(drivers.map((d) => d.code));
  };

  const handleClearAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange([]);
  };

  const filteredDrivers = drivers.filter(
    (d) =>
      d.code.toLowerCase().includes(search.toLowerCase()) ||
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.team.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div
      ref={dropdownRef}
      style={{
        position: 'relative',
        minWidth: '260px',
        maxWidth: '400px',
        flex: 1,
      }}
    >
      {/* Trigger Button */}
      <div
        onClick={() => !disabled && !loading && setIsOpen(!isOpen)}
        style={{
          backgroundColor: '#1c1c1c',
          color: disabled ? '#666' : '#e0e0e0',
          border: isOpen ? '1px solid #00CED5' : '1px solid #333',
          borderRadius: '6px',
          padding: '8px 12px',
          minHeight: '38px',
          cursor: disabled || loading ? 'not-allowed' : 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '8px',
          userSelect: 'none',
          boxSizing: 'border-box',
          transition: 'border-color 0.2s',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', alignItems: 'center' }}>
          {loading ? (
            <span style={{ color: '#888', fontSize: '13px' }}>Loading drivers...</span>
          ) : selectedDrivers.length === 0 ? (
            <span style={{ color: '#777', fontSize: '13px' }}>Select drivers...</span>
          ) : (
            selectedDrivers.map((code) => {
              const driver = drivers.find((d) => d.code === code);
              const color = driver?.color || '#00CED5';
              return (
                <span
                  key={code}
                  style={{
                    backgroundColor: '#2a2a2a',
                    borderLeft: `3px solid ${color}`,
                    color: '#fff',
                    padding: '2px 6px',
                    borderRadius: '3px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToggleDriver(code);
                  }}
                  title={`Remove ${code}`}
                >
                  {code}
                  <span style={{ color: '#888', cursor: 'pointer', fontSize: '11px', marginLeft: '2px' }}>×</span>
                </span>
              );
            })
          )}
        </div>

        <span style={{ color: '#888', fontSize: '11px', transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          ▼
        </span>
      </div>

      {/* Popover Dropdown */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            backgroundColor: '#181818',
            border: '1px solid #333',
            borderRadius: '6px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
            zIndex: 1000,
            maxHeight: '320px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Search & Actions Header */}
          <div style={{ padding: '8px', borderBottom: '1px solid #282828', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <input
              type="text"
              placeholder="Search driver or team..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                backgroundColor: '#222',
                color: '#fff',
                border: '1px solid #444',
                borderRadius: '4px',
                padding: '6px 10px',
                fontSize: '12px',
                outline: 'none',
                width: '100%',
                boxSizing: 'border-box',
              }}
              onClick={(e) => e.stopPropagation()}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
              <button
                type="button"
                onClick={handleSelectAll}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#00CED5',
                  cursor: 'pointer',
                  padding: '2px 4px',
                  fontWeight: 600,
                }}
              >
                Select All ({drivers.length})
              </button>
              <button
                type="button"
                onClick={handleClearAll}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#ff6b6b',
                  cursor: 'pointer',
                  padding: '2px 4px',
                  fontWeight: 600,
                }}
              >
                Clear All
              </button>
            </div>
          </div>

          {/* Drivers List */}
          <div style={{ overflowY: 'auto', flex: 1, padding: '4px 0' }}>
            {filteredDrivers.length === 0 ? (
              <div style={{ padding: '12px', textAlign: 'center', color: '#666', fontSize: '12px' }}>
                No drivers found
              </div>
            ) : (
              filteredDrivers.map((driver) => {
                const isSelected = selectedDrivers.includes(driver.code);
                return (
                  <div
                    key={driver.code}
                    onClick={() => handleToggleDriver(driver.code)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '7px 12px',
                      cursor: 'pointer',
                      backgroundColor: isSelected ? '#242b30' : 'transparent',
                      borderLeft: `4px solid ${driver.color || '#00CED5'}`,
                      transition: 'background-color 0.15s',
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = '#222';
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      readOnly
                      style={{ cursor: 'pointer', accentColor: '#00CED5' }}
                    />
                    <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: '#fff', fontWeight: 600, fontSize: '13px' }}>
                          {driver.code} <span style={{ fontWeight: 400, color: '#ccc' }}>({driver.name})</span>
                        </span>
                      </div>
                      {driver.team && (
                        <span style={{ color: '#777', fontSize: '11px' }}>{driver.team}</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
