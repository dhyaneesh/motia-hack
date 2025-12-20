'use client';
import { HStack, Button, Text, Badge, Box } from '@chakra-ui/react';
import { useMode, Mode } from '@/contexts/ModeContext';

export function ModeSwitcher() {
  const { currentMode, setMode } = useMode();

  const modes: { value: Mode; label: string; color: string }[] = [
    { value: 'default', label: 'Default', color: 'gray' },
    { value: 'shopping', label: 'Shopping', color: 'blue' },
    { value: 'study', label: 'Study', color: 'green' }
  ];

  return (
    <Box p={4} borderBottom="1px" borderColor="gray.200" bg="white">
      <HStack spacing={4} align="center">
        <Text fontSize="sm" fontWeight="medium" color="gray.600">
          Mode:
        </Text>
        <HStack spacing={2}>
          {modes.map((mode) => (
            <Button
              key={mode.value}
              size="sm"
              colorScheme={currentMode === mode.value ? mode.color : 'gray'}
              variant={currentMode === mode.value ? 'solid' : 'outline'}
              onClick={() => setMode(mode.value)}
            >
              {mode.label}
            </Button>
          ))}
        </HStack>
        {currentMode !== 'default' && (
          <Badge colorScheme={currentMode === 'shopping' ? 'blue' : 'green'} fontSize="xs">
            Active
          </Badge>
        )}
      </HStack>
    </Box>
  );
}
