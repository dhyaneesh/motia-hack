'use client';
import {
  Box,
  Input,
  Button,
  Image,
  VStack,
  Text,
  IconButton
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { useState, useRef } from 'react';

interface ImageSearchProps {
  onImageSelect: (imageBase64: string) => void;
  onClear: () => void;
}

export function ImageSearch({ onImageSelect, onClear }: ImageSearchProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Image size must be less than 5MB');
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      setPreview(result);
      // Convert to base64 and call callback
      const base64 = result.split(',')[1]; // Remove data:image/...;base64, prefix
      onImageSelect(base64);
    };
    reader.readAsDataURL(file);
  };

  const handleClear = () => {
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClear();
  };

  return (
    <VStack spacing={2} align="stretch">
      {preview ? (
        <Box position="relative">
          <Image
            src={preview}
            alt="Preview"
            maxH="150px"
            borderRadius="md"
            objectFit="contain"
          />
          <IconButton
            aria-label="Remove image"
            icon={<CloseIcon />}
            size="xs"
            position="absolute"
            top={1}
            right={1}
            onClick={handleClear}
            colorScheme="red"
          />
        </Box>
      ) : (
        <Box>
          <Input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            display="none"
            id="image-upload"
          />
          <Button
            as="label"
            htmlFor="image-upload"
            size="sm"
            variant="outline"
            cursor="pointer"
            w="full"
          >
            Upload Image
          </Button>
          <Text fontSize="xs" color="gray.500" mt={1} textAlign="center">
            Search by image
          </Text>
        </Box>
      )}
    </VStack>
  );
}
