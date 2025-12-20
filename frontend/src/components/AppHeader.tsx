'use client';
import { Box, Heading, Text, HStack } from '@chakra-ui/react';

export function AppHeader() {
  return (
    <Box
      p={4}
      borderBottom="1px"
      borderColor="gray.200"
      bg="white"
    >
      <HStack spacing={3} align="center">
        <Heading size="lg" color="blue.600" fontWeight="bold">
          Dive
        </Heading>
        <Text fontSize="sm" color="gray.600" fontStyle="italic">
          Searching Redefined
        </Text>
      </HStack>
    </Box>
  );
}
